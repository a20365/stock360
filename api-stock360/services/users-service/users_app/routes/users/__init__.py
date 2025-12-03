from fastapi import APIRouter

from . import get, post, put

router = APIRouter()
router.include_router(post.router, tags=["POST"])
router.include_router(put.router, tags=["PUT"])
router.include_router(get.router, tags=["GET"])
