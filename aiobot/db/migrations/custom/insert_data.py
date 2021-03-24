"""18_09_2020

Create Date: 2020-09-18 15:49:48.321080

"""
from alembic import op
import sqlalchemy as sa

import os
import sys
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(ROOT_DIR)))
sys.path.append(PARENT_DIR)

from apps.shopwatcher.tables import shop
from apps.parser.enum import Shop as ShopEnum

shops_data = [
    {'name': ShopEnum.mango.value, 'host': 'shop.mango.com', 'url': 'https://shop.mango.com', 'parse_params': {"headers": {"stock-id": "075.RU.0.false.false.v12"}}},
    {'name': ShopEnum.zara.value, 'host': 'www.zara.com', 'url': 'https://www.zara.com'},
    {'name': ShopEnum.letu.value, 'host': 'www.letu.ru', 'url': 'https://www.letu.ru'},
    {'name': ShopEnum.nike.value, 'host': 'www.nike.com', 'url': 'https://www.nike.com'},
    ]

# revision identifiers, used by Alembic.
revision = ''
down_revision = ''
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    for shop_data in shops_data:
        result = connection.execute(sa.select([shop.c.id]).where(shop.c.name==shop_data['name']))
        shop_id = result.scalar()
        if shop_id is None:
            connection.execute(shop.insert().values(**shop_data))
            

def downgrade():
    pass
