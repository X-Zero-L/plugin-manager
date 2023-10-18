from argparse import Namespace

from nonebot.matcher import Matcher
from nonebot.params import ShellCommandArgs
from nonebot.message import run_preprocessor
from nonebot.exception import IgnoredException
from nonebot.plugin import PluginMetadata, on_shell_command, get_loaded_plugins
from nonebot.adapters.onebot.v11 import Bot as V11Bot, Event as V11Event, MessageEvent as V11MessageEvent, GroupMessageEvent as V11GroupMessageEvent
from nonebot.adapters.onebot.v12 import Bot as V12Bot, Event as V12Event, MessageEvent as V12MessageEvent, GroupMessageEvent as V12GroupMessageEvent
from nonebot.adapters.red import Bot as RedBot, MessageEvent as RedMessageEvent, GroupMessageEvent as RedGroupMessageEvent
from nonebot.adapters.red.event import Event as RedEvent
from nonebot.internal.adapter.bot import Bot
from typing import Union
from nonebot_plugin_saa import Text, MessageFactory

from .handle import Handle
from .parser import npm_parser
from .manager import plugin_manager

__plugin_meta__ = PluginMetadata(
    name="插件管理器",
    description="基于 import hook 的插件管理",
    usage="""看 README""",
    type="application",
    homepage="https://github.com/nonepkg/plugin-manager",
    supported_adapters={"~onebot.v11+~onebot.v12+~red"},
)

npm = on_shell_command("npm", parser=npm_parser, priority=1)


# 在 Matcher 运行前检测其是否启用
@run_preprocessor
async def _(matcher: Matcher, bot: Bot, event: Union[V11Event, V12Event, RedEvent]):
    plugin = matcher.plugin_name

    conv = {
        "user": [],  # type: ignore
        "group": [],  # type: ignore
    }
    if isinstance(bot, V11Bot) or isinstance(bot, V12Bot):
        conv["user"] = [str(event.user_id)] # type: ignore
    elif isinstance(bot, RedBot):
        conv["user"] = [str(event.get_user_id())] # type: ignore
    
    if isinstance(event, V11GroupMessageEvent) or isinstance(event, V12GroupMessageEvent):
        conv["group"] = [str(event.group_id)] # type: ignore
    elif isinstance(event, RedGroupMessageEvent):
        conv["group"] = [str(event.peerUin or event.group_id)] # type: ignore
    
    if (
        conv["user"]
        and not conv["group"]
        and conv["user"] in bot.config.superusers  # type: ignore
    ):
        conv["user"] = [] # type: ignore
        conv["group"] = [] # type: ignore

    plugin_manager.update_plugin(
        {
            str(p.name): p.name != "nonebot_plugin_manager" and bool(p.matcher)
            for p in get_loaded_plugins()
        }
    )

    if plugin and not plugin_manager.get_plugin(conv=conv, perm=1)[plugin]: # type: ignore
        raise IgnoredException(f"Nonebot Plugin Manager has blocked {plugin} !")


@npm.handle()
async def _(bot: Bot, event: Union[V11MessageEvent, V12MessageEvent, RedMessageEvent], args: Namespace = ShellCommandArgs()):
    
    conv = {
        "user": [],  # type: ignore
        "group": [],  # type: ignore
    }
    
    if isinstance(bot, V11Bot) or isinstance(bot, V12Bot):
        conv["user"] = [str(event.user_id)] # type: ignore
    elif isinstance(bot, RedBot):
        conv["user"] = [str(event.get_user_id())] # type: ignore
    
    if isinstance(event, V11GroupMessageEvent) or isinstance(event, V12GroupMessageEvent):
        conv["group"] = [str(event.group_id)] # type: ignore
    elif isinstance(event, RedGroupMessageEvent):
        conv["group"] = [str(event.peerUin or event.group_id)] # type: ignore
    args.conv = conv
    args.is_admin = (
        conv["user"][0] in ["admin", "owner"] # type: ignore
        if isinstance(event, V11GroupMessageEvent) or isinstance(event, V12GroupMessageEvent) or isinstance(event, RedGroupMessageEvent)
        else False
    )
    args.is_superuser = conv["user"][0] in bot.config.superusers # type: ignore

    if hasattr(args, "handle"):
        message = getattr(Handle, args.handle)(args)
        if message is not None:
            message = message.split("\n")
            if len(message) > 15:
                i = 1
                messages = []
                while len(message) > 15:
                    messages.append("\n".join(message[:15]) + f"\n【第{i}页】")
                    message = message[15:]
                    i = i + 1
                messages.append("\n".join(message[:15]) + f"\n【第{i}页-完】")
                await MessageFactory(
                    [Text(m) for m in messages]
                ).send()
            else:
                await MessageFactory(
                    [Text(m+"\n") for m in message]
                ).send()
