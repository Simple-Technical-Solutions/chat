from fastapi import APIRouter

from commons import config as c
from langflow.interface.types import build_langchain_types_dict

logger = c.get_logger(__name__)


# build router
router = APIRouter(prefix="/flow", tags=["flow"])
# add docs to router
router.__doc__ = """
# Flow API
"""


@router.get("/components")
def get_all():
    return build_langchain_types_dict()
