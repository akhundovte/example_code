"""Initial

Revision ID: 71533b599a99
Revises: 
Create Date: 2021-03-16 16:39:25.852101

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '71533b599a99'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('auth_group',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=127), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__auth_group'))
    )
    op.create_table('auth_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id_orig', sa.BigInteger(), nullable=False),
    sa.Column('first_name', sa.String(length=127), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__auth_user')),
    sa.UniqueConstraint('user_id_orig', name=op.f('uq__auth_user__user_id_orig'))
    )
    op.create_table('shop',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=127), nullable=False),
    sa.Column('label', sa.String(length=127), nullable=True),
    sa.Column('domain', sa.String(length=127), nullable=True),
    sa.Column('url', sa.String(length=511), nullable=True),
    sa.Column('hostname', sa.String(length=511), nullable=True),
    sa.Column('parse_params', sa.JSON(), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=False),
    sa.Column('need_cookies', sa.Boolean(), nullable=False),
    sa.Column('sort', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__shop')),
    sa.UniqueConstraint('domain', name=op.f('uq__shop__domain'))
    )
    op.create_table('auth_user_group_ix',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('group_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['auth_group.id'], name=op.f('fk__auth_user_group_ix__group_id__auth_group'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], name=op.f('fk__auth_user_group_ix__user_id__auth_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__auth_user_group_ix')),
    sa.UniqueConstraint('user_id', 'group_id', name=op.f('uq__auth_user_group_ix__user_id_group_id'))
    )
    op.create_index(op.f('ix__auth_user_group_ix__group_id'), 'auth_user_group_ix', ['group_id'], unique=False)
    op.create_index(op.f('ix__auth_user_group_ix__user_id'), 'auth_user_group_ix', ['user_id'], unique=False)
    op.create_table('product',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=127), nullable=False),
    sa.Column('url', sa.String(length=1023), nullable=True),
    sa.Column('url_parse', sa.String(length=1023), nullable=True),
    sa.Column('reference', sa.String(length=127), nullable=True),
    sa.Column('shop_id', sa.Integer(), nullable=False),
    sa.Column('parent_id', sa.Integer(), nullable=True),
    sa.Column('dt_created', sa.DateTime(), nullable=False),
    sa.Column('parameters', sa.JSON(), nullable=True),
    sa.ForeignKeyConstraint(['parent_id'], ['product.id'], name=op.f('fk__product__parent_id__product'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['shop_id'], ['shop.id'], name=op.f('fk__product__shop_id__shop'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__product'))
    )
    op.create_index(op.f('ix__product__parent_id'), 'product', ['parent_id'], unique=False)
    op.create_index(op.f('ix__product__shop_id'), 'product', ['shop_id'], unique=False)
    op.create_table('notice_msg',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('status', sa.SmallInteger(), nullable=False),
    sa.Column('dt_send', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk__notice_msg__product_id__product'), ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], name=op.f('fk__notice_msg__user_id__auth_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__notice_msg'))
    )
    op.create_index(op.f('ix__notice_msg__dt_send'), 'notice_msg', ['dt_send'], unique=False, postgresql_where=sa.text('dt_send IS NULL'))
    op.create_index(op.f('ix__notice_msg__product_id'), 'notice_msg', ['product_id'], unique=False)
    op.create_index(op.f('ix__notice_msg__user_id'), 'notice_msg', ['user_id'], unique=False)
    op.create_table('product_stock',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('sku', sa.String(length=63), nullable=False),
    sa.Column('available', sa.Boolean(), nullable=False),
    sa.Column('price_base', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('price_sale', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('price_card', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('discount', sa.Integer(), nullable=True),
    sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk__product_stock__product_id__product'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__product_stock')),
    sa.UniqueConstraint('product_id', 'sku', name='uq__product_stock__product_id_sku')
    )
    op.create_index(op.f('ix__product_stock__product_id'), 'product_stock', ['product_id'], unique=False)
    op.create_table('sub_user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('dt_created', sa.DateTime(), nullable=False),
    sa.Column('dt_updated', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk__sub_user__product_id__product'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['auth_user.id'], name=op.f('fk__sub_user__user_id__auth_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__sub_user')),
    sa.UniqueConstraint('product_id', 'user_id', name=op.f('uq__sub_user__product_id_user_id'))
    )
    op.create_index(op.f('ix__sub_user__product_id'), 'sub_user', ['product_id'], unique=False)
    op.create_index(op.f('ix__sub_user__user_id'), 'sub_user', ['user_id'], unique=False)
    op.create_index(op.f('ix__sub_user__user_id_dt_created'), 'sub_user', ['user_id', 'dt_created'], unique=False)
    op.create_table('notice_stock',
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['stock_id'], ['product_stock.id'], name=op.f('fk__notice_stock__stock_id__product_stock'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('stock_id', name=op.f('pk__notice_stock'))
    )
    op.create_index(op.f('ix__notice_stock__stock_id'), 'notice_stock', ['stock_id'], unique=False)
    op.create_table('price_history',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_stock_id', sa.Integer(), nullable=False),
    sa.Column('price_base', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('price_sale', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('price_card', sa.Numeric(precision=10, scale=2), nullable=True),
    sa.Column('dt', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['product_stock_id'], ['product_stock.id'], name=op.f('fk__price_history__product_stock_id__product_stock'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__price_history'))
    )
    op.create_index(op.f('ix__price_history__product_stock_id'), 'price_history', ['product_stock_id'], unique=False)
    op.create_table('sub_user_stock_ix',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('stock_id', sa.Integer(), nullable=False),
    sa.Column('sub_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['stock_id'], ['product_stock.id'], name=op.f('fk__sub_user_stock_ix__stock_id__product_stock'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['sub_id'], ['sub_user.id'], name=op.f('fk__sub_user_stock_ix__sub_id__sub_user'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__sub_user_stock_ix')),
    sa.UniqueConstraint('stock_id', 'sub_id', name=op.f('uq__sub_user_stock_ix__stock_id_sub_id'))
    )
    op.create_index(op.f('ix__sub_user_stock_ix__stock_id'), 'sub_user_stock_ix', ['stock_id'], unique=False)
    op.create_index(op.f('ix__sub_user_stock_ix__sub_id'), 'sub_user_stock_ix', ['sub_id'], unique=False)
    op.create_table('invest_security',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('ticker', sa.String(length=10), nullable=False),
    sa.Column('name', sa.String(length=127), nullable=True),
    sa.Column('short_name', sa.String(length=127), nullable=True),
    sa.Column('is_collect', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__invest_security')),
    sa.UniqueConstraint('ticker', name=op.f('uq__invest_security__ticker'))
    )
    op.create_table('invest_trade_history',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('trade_no', sa.BigInteger(), nullable=True),
    sa.Column('board', sa.String(length=10), nullable=True),
    sa.Column('dt_trade', sa.DateTime(), nullable=True),
    sa.Column('price', sa.Numeric(precision=20, scale=10), nullable=True),
    sa.Column('quantity', sa.Integer(), nullable=True),
    sa.Column('value', sa.Numeric(precision=20, scale=10), nullable=True),
    sa.Column('period', sa.String(length=10), nullable=True),
    sa.Column('type_trade', sa.String(length=1), nullable=True),
    sa.Column('tradetime_grp', sa.BigInteger(), nullable=True),
    sa.Column('dt_created', sa.DateTime(), nullable=False),
    sa.Column('security_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['security_id'], ['invest_security.id'], name=op.f('fk__invest_trade_history__security_id__invest_security'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk__invest_trade_history')),
    sa.UniqueConstraint('trade_no', name=op.f('uq__invest_trade_history__trade_no'))
    )
    op.create_index(op.f('ix__invest_trade_history__security_id'), 'invest_trade_history', ['security_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix__invest_trade_history__security_id'), table_name='invest_trade_history')
    op.drop_table('invest_trade_history')
    op.drop_table('invest_security')
    op.drop_index(op.f('ix__sub_user_stock_ix__sub_id'), table_name='sub_user_stock_ix')
    op.drop_index(op.f('ix__sub_user_stock_ix__stock_id'), table_name='sub_user_stock_ix')
    op.drop_table('sub_user_stock_ix')
    op.drop_index(op.f('ix__price_history__product_stock_id'), table_name='price_history')
    op.drop_table('price_history')
    op.drop_index(op.f('ix__notice_stock__stock_id'), table_name='notice_stock')
    op.drop_table('notice_stock')
    op.drop_index(op.f('ix__sub_user__user_id_dt_created'), table_name='sub_user')
    op.drop_index(op.f('ix__sub_user__user_id'), table_name='sub_user')
    op.drop_index(op.f('ix__sub_user__product_id'), table_name='sub_user')
    op.drop_table('sub_user')
    op.drop_index(op.f('ix__product_stock__product_id'), table_name='product_stock')
    op.drop_table('product_stock')
    op.drop_index(op.f('ix__notice_msg__user_id'), table_name='notice_msg')
    op.drop_index(op.f('ix__notice_msg__product_id'), table_name='notice_msg')
    op.drop_index(op.f('ix__notice_msg__dt_send'), table_name='notice_msg')
    op.drop_table('notice_msg')
    op.drop_index(op.f('ix__product__shop_id'), table_name='product')
    op.drop_index(op.f('ix__product__parent_id'), table_name='product')
    op.drop_table('product')
    op.drop_index(op.f('ix__auth_user_group_ix__user_id'), table_name='auth_user_group_ix')
    op.drop_index(op.f('ix__auth_user_group_ix__group_id'), table_name='auth_user_group_ix')
    op.drop_table('auth_user_group_ix')
    op.drop_table('shop')
    op.drop_table('auth_user')
    op.drop_table('auth_group')
    # ### end Alembic commands ###
