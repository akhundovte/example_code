
from typing import (
    List, Optional, Mapping, Tuple
)

from marshmallow import ValidationError

# from utils.timezone import now
from core.exceptions import ObjectDoesNotExist

from .exceptions import DeserializeProductError
from ..serializers import product_schema
from ..datacls import Product  # , Shop


class ProductService:
    templ_msg_change_admin = ("Изменение строки из таблицы %s - id %d, поле %s:"
                              " old value '%s', new value '%s'")
    templ_msg_delete_admin = ("Удаление строки из таблицы %s - id %d\n%s")
    templ_msg_not_available_admin = ("Установка not available для строки из таблицы %s - id %d\n%s")

    def __init__(self, product_repository, notice_repository) -> None:
        self._product_repository = product_repository
        self._notice_repository = notice_repository

    async def handle(
        self,
        product_data: dict,
        shop_id: int,
        parent_product: Optional[Product] = None,
        delete_not_exists_stock: bool = True
    ) -> None:
        """Обработка данных полученных после парсинга страницы товара."""
        if delete_not_exists_stock is None:
            delete_not_exists_stock = True

        msg_admins = None
        try:
            product_new = self._generate_product_from_data(product_data, shop_id, parent_product)
        except DeserializeProductError as e:
            raise e

        try:
            product_cur = await self._get_product_from_repository(product_new.reference, shop_id)
            product_new.id = product_cur.id
            msg_admin_rows, notice_struct = await self._update_product_and_stocks(
                product_new, product_cur, delete_not_exists_stock)
            await self._save_notice(notice_struct)
            msg_admins = await self._get_msg_admins(msg_admin_rows)
        except ObjectDoesNotExist:
            product_new.id = await self._create_product_and_stocks(product_new)
        return product_new, msg_admins

    def _generate_product_from_data(self, product_data, shop_id, parent_product):
        product_clean_data = self._deserialize_data(product_data)
        product_clean_data['shop_id'] = shop_id
        if parent_product:
            product_clean_data['parent_id'] = parent_product.id
        return Product.from_dict(product_clean_data)

    def _deserialize_data(self, product_data):
        try:
            return product_schema.load(product_data)
        except ValidationError as err:
            raise DeserializeProductError('Ошибка валидации', errors=err.messages)

    async def _get_product_from_repository(self, reference, shop_id):
        return await self._product_repository.get_product_by_reference(
            reference, shop_id)

    async def _create_product_and_stocks(self, product_new):
        return await self._product_repository.create_product_and_stocks(product_new)

    async def _update_product_and_stocks(self, product_new, product_cur, delete_not_exists_stock):
        msg_admin_rows = []
        update_product_data = self._check_product(product_new, product_cur, msg_admin_rows)
        stocks_create, stocks_update_data, stocks_delete_ids, notice_struct = \
            await self._check_product_stocks(
                product_new, product_cur, msg_admin_rows, delete_not_exists_stock)

        await self._product_repository.update_product_and_stocks(
            product_cur.id,
            update_product_data,
            stocks_create,
            stocks_update_data,
            stocks_delete_ids,
            delete_not_exists_stock
            )
        return msg_admin_rows, notice_struct

    def _check_product(self, product_new, product_cur, msg_admin_rows):
        """Проверяем актуальность данных для product
        """
        update_product_data = {}
        fields_product = ('name', 'url', 'url_parse', 'parameters', 'parent_id')
        for field in fields_product:
            val_new = getattr(product_new, field)
            val_cur = getattr(product_cur, field)
            if val_new != val_cur:
                update_product_data[field] = val_new
                msg_row = self.templ_msg_change_admin % ('product', product_cur.id, field, val_cur, val_new)
                msg_admin_rows.append(msg_row)
        return update_product_data

    async def _check_product_stocks(
        self, product_new, product_cur, msg_admin_rows, delete_not_exists_stock
    ):
        notice_data = {}
        available_stock_ids = set()
        # делаем словарь на основе списка, чтобы при сравнении быстро доставать данные
        stocks_new = {item.sku: item for item in product_new.stocks}
        stocks_update_data = {}
        stocks_delete_ids = []

        for stock_cur in product_cur.stocks:
            stock_new = stocks_new.get(stock_cur.sku)
            if stock_new is not None:
                update_data, price_change, became_available = \
                    await self._check_stock(stock_cur, stock_new, msg_admin_rows)
                if update_data:
                    stocks_update_data[stock_cur.id] = update_data

                self._set_notice_data_stock(stock_cur.id, price_change, became_available, notice_data)
                if stock_new.available:
                    available_stock_ids.add(stock_cur.id)
                # удаляем, чтобы после цикла остались только новые данные, которые надо сохранить
                del stocks_new[stock_cur.sku]
            else:
                stock_id = self._check_delete_stock(
                    product_cur.id, stock_cur, msg_admin_rows, delete_not_exists_stock)
                if stock_id:
                    stocks_delete_ids.append(stock_id)

        if notice_data:
            notice_struct = {'data': notice_data, 'available_stock_ids': available_stock_ids}
        else:
            notice_struct = None

        # if stocks_new:  # если остались данные, то это новые, которых нет в БД
        return list(stocks_new.values()), stocks_update_data, stocks_delete_ids, notice_struct

    async def _check_stock(self, stock_cur, stock_new, msg_admin_rows):
        update_data = {}
        stock_id = stock_cur.id

        self._check_parameters_stock(
            stock_id, stock_cur.parameters, stock_new.parameters, update_data, msg_admin_rows
            )
        price_change = self._check_price_stock(
            stock_cur, stock_new, update_data
            )
        became_available = self._check_available_stock(
            stock_id, stock_cur.available, stock_new.available, update_data
            )
        if price_change:
            await self._product_repository.create_price_history(stock_cur)

        return update_data, price_change, became_available

    def _set_notice_data_stock(self, stock_id, price_change, became_available, notice_data):
        """
        оповещаем
            если изменилась цена для всех sku
            (а не только для доступных sku, чтобы была больше заинтересованность)
            если цена не изменилась, но стал доступным данный sku
        """
        notice_data_stock = {}
        if price_change:
            notice_data_stock['price'] = price_change
        elif became_available:
            notice_data_stock['available'] = True

        if notice_data_stock:
            notice_data[stock_id] = notice_data_stock

    def _check_delete_stock(self, product_id, stock_cur, msg_admin_rows, delete_not_exists_stock):
        """
        Удаляем запись stock
            если для данного магазина удаляются stocks, которые отсутствуют после парсинга
            если для магазина такие записи надо делать просто недоступными (available=False),
            то смотрим на параметр available (чтобы не делать лишних действий)
        """
        text = (f"product_id: {product_id}\nsku: {stock_cur.sku}\n")
        if delete_not_exists_stock:
            msg_row = self.templ_msg_delete_admin % ('product_stock', stock_cur.id, text)
            msg_admin_rows.append(msg_row)
            return stock_cur.id
        else:
            if stock_cur.available:
                msg_row = self.templ_msg_not_available_admin % ('product_stock', stock_cur.id, text)
                msg_admin_rows.append(msg_row)
                return stock_cur.id

    def _check_available_stock(self, stock_id, val_old, val_new, update_data):
        if val_old != val_new:
            update_data['available'] = val_new
            if val_new:
                return True
        return False

    def _check_price_stock(self, stock_cur, stock_new, update_data):
        """
        """
        # если убирается цена с сайта не отправляем сообщение и не сохраняем ничего в БД
        if stock_cur.price_sale is not None and stock_new.price_sale is None:
            return

        price_change = {}
        for field in ('price_base', 'price_sale', 'price_card'):
            val_old = getattr(stock_cur, field)
            val_new = getattr(stock_new, field)
            if val_old != val_new:
                update_data[field] = val_new
                price_change[field.rsplit('_', 1)[1]] = (val_old, val_new)

        if price_change:
            # это условие, чтобы если нет скидки, а просто меняется базовая цена (price_base=price_sale)
            # формировать более корректное сообщение для пользователя
            if 'price_base' in price_change and 'price_sale' in price_change:
                if price_change['price_base'][1] == price_change['price_sale'][1]:
                    del price_change['price_base']

        if stock_new.discount != stock_cur.discount:
            update_data['discount'] = stock_new.discount

        return price_change

    def _check_parameters_stock(self, stock_id, val_old, val_new, update_data, msg_admin_rows):
        if val_old != val_new:
            update_data['parameters'] = val_new
            msg_row = self.templ_msg_change_admin % ('product_stock', stock_id, 'parameters', val_old, val_new)
            msg_admin_rows.append(msg_row)

    async def _save_notice(self, notice_struct):
        """
        """
        if not notice_struct:
            return

        notice_data = notice_struct['data']
        available_stock_ids = notice_struct['available_stock_ids']

        stock_ids = notice_data.keys()
        notice_stocks_bd = await self._notice_repository.get_notice_stocks(stock_ids)

        if not notice_stocks_bd:
            await self._notice_repository.save_notice_stocks(notice_data)
        else:
            # сравниваем данные из БД с актуальными
            update_notice_data = {}
            delete_notice_ids = []
            for notice_stock_bd in notice_stocks_bd:
                data_change = None
                notice_stock_data_new = notice_data.get(notice_stock_bd.stock_id)
                if notice_stock_data_new is not None:
                    data_change = self._check_change_notice_stock(
                        notice_stock_bd.data, notice_stock_data_new
                        )
                    if data_change:
                        update_notice_data[notice_stock_bd.stock_id] = data_change
                    del notice_data[notice_stock_bd.stock_id]
                else:
                    notice_stock_id = self._check_delete_notice_stock(
                        notice_stock_bd, available_stock_ids)
                    if notice_stock_id:
                        delete_notice_ids.append(notice_stock_id)

            await self._notice_repository.save_notice_stocks(
                notice_data, update_notice_data, delete_notice_ids
                )

    def _check_change_notice_stock(self, notice_stock_data_bd, notice_stock_data_new):
        """
        Бывают случаи изменения разных цен base, sale
        поэтому используем слияние словарей, чтобы осталось старое значение
        причем если ключ одинаковый старое заменится новым
        """
        data_change = None
        if (notice_stock_data_new != notice_stock_data_bd and 'price' in notice_stock_data_new):
            if 'price' in notice_stock_data_bd:
                data_change = {'price': {**notice_stock_data_bd['price'], **notice_stock_data_new['price']}}
            else:
                data_change = notice_stock_data_new

        return data_change

    def _check_delete_notice_stock(self, notice_stock_bd, available_stock_ids):
        if ('available' in notice_stock_bd.data and
                notice_stock_bd.stock_id not in available_stock_ids):
            return notice_stock_bd.id

    async def _get_msg_admins(self, msg_admin_rows):
        if msg_admin_rows:
            msg_text = ''
            for msg_row in msg_admin_rows:
                msg_text += msg_row + '\n'
            return msg_text


class ProductSubService:
    def __init__(self, product_sub_repository) -> None:
        self._product_sub_repository = product_sub_repository

    async def get_product_for_edit_sub(self, sub_id, user_id):
        product = await self._product_sub_repository.get_product_for_sub(sub_id, user_id)
        return product

    async def get_product_parse_data(self):
        rows = []
        async for item in self._product_sub_repository.get_product_for_sub_iter():
            if not item.url_parse:
                raise ValueError('url_parse must be set')
            kwargs_handler = {
                'url': item.url_parse, 'url_product': item.url,
                'shop_id': item.shop_id, 'shop_name': item.shop_name
                }
            headers = None
            cookies = None
            parse_params = item.parse_params
            if parse_params:
                headers = parse_params.get('headers')
                cookies = parse_params.get('cookies')
                kwargs_handler = {**kwargs_handler, **item.parse_params}
            rows.append({'url': item.url_parse, 'headers': headers, 'cookies': cookies, 'kwargs': kwargs_handler})
        return rows
