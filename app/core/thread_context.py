# @description: 
# @author: licanglong
# @date: 2025/12/26 16:25
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token

from pydantic import ConfigDict, BaseModel


class ThreadContextData(BaseModel):
    """
    线程上下文数据模型
    """

    def fork(self) -> "ThreadContextData":
        """
        为子线程创建“隔离但安全”的上下文副本
        """
        return ThreadContextData(
            # 资源对象：共享（不可深拷贝）
            # ...

            # 可变数据：隔离
            # ...
        )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,  # 运行时赋值校验
        extra="forbid",  # 禁止未声明字段
        frozen=False,  # 允许修改（上下文需要）
    )


class ThreadContext:
    _context_var: ContextVar[ThreadContextData] = ContextVar(
        "thread_context",
        default=ThreadContextData(),
    )

    @classmethod
    def get(cls) -> ThreadContextData:
        return cls._context_var.get()

    @classmethod
    def set(cls, context: ThreadContextData) -> Token:
        """
        设置完整上下文，返回 token 用于回滚
        """
        return cls._context_var.set(context)

    @classmethod
    def reset(cls, token: Token) -> None:
        """
        回滚到上一个上下文
        """
        cls._context_var.reset(token)

    @classmethod
    def clear(cls) -> None:
        """
        重置为一个全新上下文
        """
        cls._context_var.set(ThreadContextData())


@asynccontextmanager
async def use_thread_context(ctx: ThreadContextData):
    """
    在 async 调用链中安全注入 ThreadContext
    @case:
    ```
    async with use_thread_context(ctx):
        await do_work()
    ```
    """
    token = ThreadContext.set(ctx)
    try:
        yield ctx
    finally:
        ThreadContext.reset(token)
