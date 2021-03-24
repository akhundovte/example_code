from enum import Enum, unique, IntEnum

from sqlalchemy import (
    MetaData, Table, Column,
    Integer, String, DateTime, ForeignKey,
    Numeric, BigInteger, Boolean, UniqueConstraint, Text, Index, false,
    JSON, SmallInteger, text
    )

from sqlalchemy.dialects.postgresql import JSONB


from db.schema import convention
from utils.timezone import now

metadata = MetaData(naming_convention=convention)


@unique
class GroupEnum(Enum):
    admin = 'admin'
    subscriber = 'subscriber'


@unique
class StatusNoticeEnum(IntEnum):
    not_send = 0
    in_progress = 1
    sended = 2


user = Table(
    'auth_user', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id_orig', BigInteger, nullable=False, unique=True),
    Column('first_name', String(127), nullable=True),
    )

group = Table(
    'auth_group', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(127), nullable=True),
    )

user_group_ix = Table(
    'auth_user_group_ix', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer,
           ForeignKey('auth_user.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('group_id', Integer,
           ForeignKey('auth_group.id', ondelete='CASCADE'),
           index=True, nullable=False),
    # индексы и ограничения
    UniqueConstraint('user_id', 'group_id'),
    )


shop = Table(
    'shop', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(127), nullable=False),
    Column('label', String(127), nullable=True),
    Column('domain', String(127), nullable=True, unique=True),
    Column('url', String(511), nullable=True),
    Column('hostname', String(511), nullable=True),
    Column('parse_params', JSON, nullable=True),
    Column('enabled', Boolean, nullable=False, default=True),
    Column('need_cookies', Boolean, nullable=False, default=False),
    Column('sort', SmallInteger, default=0),
    )


product = Table(
    'product', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(127), nullable=False),
    Column('url', String(1023), nullable=True),
    Column('url_parse', String(1023), nullable=True),
    Column('reference', String(127), nullable=True),
    Column('shop_id', Integer,
           ForeignKey('shop.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('parent_id', Integer,
           ForeignKey('product.id', ondelete='CASCADE'),
           index=True, nullable=True),
    Column('dt_created', DateTime, default=now, nullable=False),
    Column('parameters', JSON, nullable=True),
    )


product_stock = Table(
    'product_stock', metadata,
    Column('id', Integer, primary_key=True),
    Column('product_id', Integer,
           ForeignKey('product.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('sku', String(63), nullable=False),
    Column('available', Boolean, default=False, nullable=False),
    Column('price_base', Numeric(precision=10, scale=2, asdecimal=True), nullable=True),
    Column('price_sale', Numeric(precision=10, scale=2, asdecimal=True), nullable=True),
    Column('price_card', Numeric(precision=10, scale=2, asdecimal=True), nullable=True),
    Column('discount', Integer, nullable=True),
    Column('parameters', JSONB, nullable=True),
    # индексы и ограничения
    UniqueConstraint('product_id', 'sku', name='uq__product_stock__product_id_sku'),
    )


price_history = Table(
    'price_history', metadata,
    Column('id', Integer, primary_key=True),
    Column('product_stock_id', Integer,
           ForeignKey('product_stock.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('price_base', Numeric(precision=10, scale=2, asdecimal=True), nullable=True),
    Column('price_sale', Numeric(precision=10, scale=2, asdecimal=True), nullable=True),
    Column('price_card', Numeric(precision=10, scale=2, asdecimal=True), nullable=True),
    Column('dt', DateTime, nullable=False),
    )


sub_user = Table(
    'sub_user', metadata,
    Column('id', Integer, primary_key=True),
    Column('product_id', Integer,
           ForeignKey('product.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('user_id', Integer,
           ForeignKey('auth_user.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('dt_created', DateTime, default=now, nullable=False),
    Column('dt_updated', DateTime, nullable=True),
    # индексы и ограничения
    UniqueConstraint('product_id', 'user_id'),
    Index(None, 'user_id', 'dt_created'),
    )


sub_user_stock_ix = Table(
    'sub_user_stock_ix', metadata,
    Column('id', Integer, primary_key=True),
    Column('stock_id', Integer,
           ForeignKey('product_stock.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('sub_id', Integer,
           ForeignKey('sub_user.id', ondelete='CASCADE'),
           index=True, nullable=False),
    # индексы и ограничения
    UniqueConstraint('stock_id', 'sub_id'),
    )


# OneToOne к product_stock
notice_stock = Table(
    'notice_stock', metadata,
    Column('stock_id', Integer,
           ForeignKey('product_stock.id', ondelete='CASCADE'),
           index=True, nullable=False, primary_key=True),
    Column('data', JSONB, nullable=True),
    )


notice_msg = Table(
    'notice_msg', metadata,
    Column('id', Integer, primary_key=True),
    Column('user_id', Integer,
           ForeignKey('auth_user.id', ondelete='CASCADE'),
           index=True, nullable=False),
    Column('product_id', Integer,
           ForeignKey('product.id', ondelete='SET NULL'),
           index=True, nullable=True),
    Column('text', Text, nullable=False),
    Column('status', SmallInteger, nullable=False, default=StatusNoticeEnum.not_send.value),
    Column('dt_send', DateTime, nullable=True),

    Index(None, 'dt_send',
          postgresql_where=(Column('dt_send').is_(None))
          ),
    Index(None, 'status', postgresql_where=(Column('status') == StatusNoticeEnum.not_send.value)),
    )
