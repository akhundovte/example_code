
from decimal import Decimal, ROUND_HALF_UP

from utils.jinja2 import jinja_render


class NoticeMessageService:

    def __init__(self, notice_msg_repository) -> None:
        self._notice_msg_repository = notice_msg_repository

    async def get_message_iter(self):
        async for user_id, user_name, text in self._notice_msg_repository.notice_msg_for_send_iter():
            yield user_id, user_name, text

    async def clear_notice_stocks(self):
        await self._notice_msg_repository.delete_all_notice_stocks()

    async def create_messages(self):
        bulk_size = 10
        bulk_data = []
        count = 0
        async for user_id, product_id, text_msg in self._messages_for_create_iter():
            if count == bulk_size:
                await self._notice_msg_repository.create_notice_msgs(bulk_data)
                bulk_data.clear()
                count = 0
            bulk_data.append({'user_id': user_id, 'product_id': product_id, 'text': text_msg})
            count += 1
        if bulk_data:
            await self._notice_msg_repository.create_notice_msgs(bulk_data)

    async def _messages_for_create_iter(self):
        async for notice_product_item in self._notice_msg_repository.get_notice_product_iter():
            context = self._get_context_msg(notice_product_item)
            text_msg = self._get_text_msg(context)
            yield notice_product_item.user_id, notice_product_item.product_id, text_msg

    def _get_context_msg(self, notice_product_item):
        """
        Это надо переделать, слишком разные случаи!!!
        может сделать разные шаблоны для сообщений (в зависимости от того, есть типы у товара или нет)
        """
        context = {
            'product_name': notice_product_item.product_name,
            'product_url': notice_product_item.product_url,
            'product_reference': notice_product_item.product_reference,
            'shop_label': notice_product_item.shop_label,
            }
        product_parameters = notice_product_item.product_parameters
        if product_parameters:
            types = self._get_product_types(product_parameters['types'])
            context['type_label'] = product_parameters.get('type_label')
            context['option_label'] = product_parameters.get('option_label')
            data_msg_d = {}
            for data_item in notice_product_item.notice_data:
                change_data = data_item['data']
                if 'price' in change_data:
                    self._edit_change_price_data(change_data['price'])
                change_data_extend = {
                    'change': change_data,
                    'discount': data_item['discount']
                    }
                change_data_extend['option'] = data_item['parameters'].get('option_name')
                type_code = data_item['parameters']['type_code']
                if type_code not in data_msg_d:
                    data_msg_d[type_code] = {
                        'url': types[type_code].get('url'),
                        'name': types[type_code].get('name'),
                        'data': [change_data_extend, ]
                        }
                else:
                    data_msg_d[type_code]['data'].append(change_data_extend)
            data_msg = data_msg_d.values()
        else:
            data_msg = []
            for data_item in notice_product_item.notice_data:
                change_data = data_item['data']
                if 'price' in change_data:
                    self._edit_change_price_data(change_data['price'])
                change_data_extend = {
                    'change': change_data,
                    'discount': data_item['discount']
                    }
                if data_item['parameters']:
                    change_data_extend['option'] = data_item['parameters'].get('option_name')
                data_msg.append({
                    'data': [change_data_extend, ]
                    })

        context['data_msg'] = data_msg
        return context

    def _get_text_msg(self, context):
        return jinja_render.render_template('notice_msg.html', context)

    def _get_product_types(self, types):
        types_d = {}
        for item in types:
            types_d[item['code']] = item
        return types_d

    def _edit_change_price_data(self, change_price_data):
        for key, val in change_price_data.items():
            old_val = val[0]
            new_val = val[1]
            diff_val = None
            if old_val is not None and new_val is not None:
                old_val = Decimal(old_val)
                new_val = Decimal(new_val)
                diff_val = 100 - ((100 * new_val)/old_val)
                if abs(diff_val) < 1:
                    diff_val = diff_val.quantize(
                        Decimal(1).scaleb(-2), rounding=ROUND_HALF_UP
                        )
                else:
                    diff_val = int(diff_val)
            change_price_data[key] = {'old': old_val, 'new': new_val, 'diff': diff_val}
