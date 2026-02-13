"""Configuration schema for MicroPython - no Pydantic dependency.

Provides ConfigBase as a lightweight replacement for Pydantic BaseModel,
with to_dict() / from_dict() for JSON serialization.
"""


class ConfigBase:
    """Base for all configuration classes. Replaces Pydantic BaseModel."""

    # Subclasses override to declare nested ConfigBase fields:
    #   {field_name: ConfigClass}
    _nested = {}
    # For dict fields whose values are ConfigBase:
    #   {field_name: ConfigClass}
    _nested_map = {}

    def to_dict(self):
        """Serialize to dict (replaces Pydantic model_dump)."""
        result = {}
        for key, val in self.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(val, ConfigBase):
                result[key] = val.to_dict()
            elif isinstance(val, list):
                result[key] = [
                    v.to_dict() if isinstance(v, ConfigBase) else v
                    for v in val
                ]
            elif isinstance(val, dict):
                result[key] = {
                    k: (v.to_dict() if isinstance(v, ConfigBase) else v)
                    for k, v in val.items()
                }
            else:
                result[key] = val
        return result

    @classmethod
    def from_dict(cls, data):
        """Deserialize from dict (replaces Pydantic model_validate)."""
        if not data:
            return cls()
        kwargs = {}
        for k, v in data.items():
            if k in cls._nested and isinstance(v, dict):
                kwargs[k] = cls._nested[k].from_dict(v)
            elif k in cls._nested_map and isinstance(v, dict):
                val_cls = cls._nested_map[k]
                kwargs[k] = {
                    mk: val_cls.from_dict(mv) if isinstance(mv, dict) else mv
                    for mk, mv in v.items()
                }
            else:
                kwargs[k] = v
        return cls(**kwargs)


# ---------------------------------------------------------------------------
# Channel configurations
# ---------------------------------------------------------------------------

class WhatsAppConfig(ConfigBase):
    """WhatsApp channel configuration."""

    def __init__(self, enabled=False, bridge_url="ws://localhost:3001",
                 bridge_token="", allow_from=None):
        self.enabled = enabled
        self.bridge_url = bridge_url
        self.bridge_token = bridge_token
        self.allow_from = allow_from if allow_from is not None else []


class TelegramConfig(ConfigBase):
    """Telegram channel configuration."""

    def __init__(self, enabled=False, token="", allow_from=None, proxy=None):
        self.enabled = enabled
        self.token = token
        self.allow_from = allow_from if allow_from is not None else []
        self.proxy = proxy


class FeishuConfig(ConfigBase):
    """Feishu/Lark channel configuration using WebSocket long connection."""

    def __init__(self, enabled=False, app_id="", app_secret="",
                 encrypt_key="", verification_token="", allow_from=None):
        self.enabled = enabled
        self.app_id = app_id
        self.app_secret = app_secret
        self.encrypt_key = encrypt_key
        self.verification_token = verification_token
        self.allow_from = allow_from if allow_from is not None else []


class DingTalkConfig(ConfigBase):
    """DingTalk channel configuration using Stream mode."""

    def __init__(self, enabled=False, client_id="", client_secret="",
                 allow_from=None):
        self.enabled = enabled
        self.client_id = client_id
        self.client_secret = client_secret
        self.allow_from = allow_from if allow_from is not None else []


class DiscordConfig(ConfigBase):
    """Discord channel configuration."""

    def __init__(self, enabled=False, token="", allow_from=None,
                 gateway_url="wss://gateway.discord.gg/?v=10&encoding=json",
                 intents=37377):
        self.enabled = enabled
        self.token = token
        self.allow_from = allow_from if allow_from is not None else []
        self.gateway_url = gateway_url
        self.intents = intents  # GUILDS + GUILD_MESSAGES + DIRECT_MESSAGES + MESSAGE_CONTENT


class EmailConfig(ConfigBase):
    """Email channel configuration (IMAP inbound + SMTP outbound)."""

    def __init__(self, enabled=False, consent_granted=False,
                 imap_host="", imap_port=993, imap_username="",
                 imap_password="", imap_mailbox="INBOX", imap_use_ssl=True,
                 smtp_host="", smtp_port=587, smtp_username="",
                 smtp_password="", smtp_use_tls=True, smtp_use_ssl=False,
                 from_address="",
                 auto_reply_enabled=True, poll_interval_seconds=30,
                 mark_seen=True, max_body_chars=12000,
                 subject_prefix="Re: ", allow_from=None):
        self.enabled = enabled
        self.consent_granted = consent_granted
        # IMAP (receive)
        self.imap_host = imap_host
        self.imap_port = imap_port
        self.imap_username = imap_username
        self.imap_password = imap_password
        self.imap_mailbox = imap_mailbox
        self.imap_use_ssl = imap_use_ssl
        # SMTP (send)
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.smtp_use_tls = smtp_use_tls
        self.smtp_use_ssl = smtp_use_ssl
        self.from_address = from_address
        # Behavior
        self.auto_reply_enabled = auto_reply_enabled
        self.poll_interval_seconds = poll_interval_seconds
        self.mark_seen = mark_seen
        self.max_body_chars = max_body_chars
        self.subject_prefix = subject_prefix
        self.allow_from = allow_from if allow_from is not None else []


class MochatMentionConfig(ConfigBase):
    """Mochat mention behavior configuration."""

    def __init__(self, require_in_groups=False):
        self.require_in_groups = require_in_groups


class MochatGroupRule(ConfigBase):
    """Mochat per-group mention requirement."""

    def __init__(self, require_mention=False):
        self.require_mention = require_mention


class MochatConfig(ConfigBase):
    """Mochat channel configuration."""

    _nested = {'mention': MochatMentionConfig}
    _nested_map = {'groups': MochatGroupRule}

    def __init__(self, enabled=False, base_url="https://mochat.io",
                 socket_url="", socket_path="/socket.io",
                 socket_disable_msgpack=False,
                 socket_reconnect_delay_ms=1000,
                 socket_max_reconnect_delay_ms=10000,
                 socket_connect_timeout_ms=10000,
                 refresh_interval_ms=30000, watch_timeout_ms=25000,
                 watch_limit=100, retry_delay_ms=500,
                 max_retry_attempts=0, claw_token="",
                 agent_user_id="", sessions=None, panels=None,
                 allow_from=None, mention=None, groups=None,
                 reply_delay_mode="non-mention", reply_delay_ms=120000):
        self.enabled = enabled
        self.base_url = base_url
        self.socket_url = socket_url
        self.socket_path = socket_path
        self.socket_disable_msgpack = socket_disable_msgpack
        self.socket_reconnect_delay_ms = socket_reconnect_delay_ms
        self.socket_max_reconnect_delay_ms = socket_max_reconnect_delay_ms
        self.socket_connect_timeout_ms = socket_connect_timeout_ms
        self.refresh_interval_ms = refresh_interval_ms
        self.watch_timeout_ms = watch_timeout_ms
        self.watch_limit = watch_limit
        self.retry_delay_ms = retry_delay_ms
        self.max_retry_attempts = max_retry_attempts  # 0 means unlimited retries
        self.claw_token = claw_token
        self.agent_user_id = agent_user_id
        self.sessions = sessions if sessions is not None else []
        self.panels = panels if panels is not None else []
        self.allow_from = allow_from if allow_from is not None else []
        self.mention = mention if mention is not None else MochatMentionConfig()
        self.groups = groups if groups is not None else {}
        self.reply_delay_mode = reply_delay_mode
        self.reply_delay_ms = reply_delay_ms


class SlackDMConfig(ConfigBase):
    """Slack DM policy configuration."""

    def __init__(self, enabled=True, policy="open", allow_from=None):
        self.enabled = enabled
        self.policy = policy
        self.allow_from = allow_from if allow_from is not None else []


class SlackConfig(ConfigBase):
    """Slack channel configuration."""

    _nested = {'dm': SlackDMConfig}

    def __init__(self, enabled=False, mode="socket",
                 webhook_path="/slack/events", bot_token="",
                 app_token="", user_token_read_only=True,
                 group_policy="mention", group_allow_from=None,
                 dm=None):
        self.enabled = enabled
        self.mode = mode
        self.webhook_path = webhook_path
        self.bot_token = bot_token
        self.app_token = app_token
        self.user_token_read_only = user_token_read_only
        self.group_policy = group_policy
        self.group_allow_from = group_allow_from if group_allow_from is not None else []
        self.dm = dm if dm is not None else SlackDMConfig()


class QQConfig(ConfigBase):
    """QQ channel configuration using botpy SDK."""

    def __init__(self, enabled=False, app_id="", secret="",
                 allow_from=None):
        self.enabled = enabled
        self.app_id = app_id
        self.secret = secret
        self.allow_from = allow_from if allow_from is not None else []


class ChannelsConfig(ConfigBase):
    """Configuration for chat channels."""

    _nested = {
        'whatsapp': WhatsAppConfig,
        'telegram': TelegramConfig,
        'discord': DiscordConfig,
        'feishu': FeishuConfig,
        'mochat': MochatConfig,
        'dingtalk': DingTalkConfig,
        'email': EmailConfig,
        'slack': SlackConfig,
        'qq': QQConfig,
    }

    def __init__(self, whatsapp=None, telegram=None, discord=None,
                 feishu=None, mochat=None, dingtalk=None, email=None,
                 slack=None, qq=None):
        self.whatsapp = whatsapp if whatsapp is not None else WhatsAppConfig()
        self.telegram = telegram if telegram is not None else TelegramConfig()
        self.discord = discord if discord is not None else DiscordConfig()
        self.feishu = feishu if feishu is not None else FeishuConfig()
        self.mochat = mochat if mochat is not None else MochatConfig()
        self.dingtalk = dingtalk if dingtalk is not None else DingTalkConfig()
        self.email = email if email is not None else EmailConfig()
        self.slack = slack if slack is not None else SlackConfig()
        self.qq = qq if qq is not None else QQConfig()


# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------

class AgentDefaults(ConfigBase):
    """Default agent configuration."""

    def __init__(self, workspace="~/.nanobot/workspace",
                 model="anthropic/claude-opus-4-5", max_tokens=8192,
                 temperature=0.7, max_tool_iterations=20,
                 memory_window=50):
        self.workspace = workspace
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_tool_iterations = max_tool_iterations
        self.memory_window = memory_window


class AgentsConfig(ConfigBase):
    """Agent configuration."""

    _nested = {'defaults': AgentDefaults}

    def __init__(self, defaults=None):
        self.defaults = defaults if defaults is not None else AgentDefaults()


# ---------------------------------------------------------------------------
# LLM provider configuration
# ---------------------------------------------------------------------------

class ProviderConfig(ConfigBase):
    """LLM provider configuration."""

    def __init__(self, api_key="", api_base=None, extra_headers=None):
        self.api_key = api_key
        self.api_base = api_base
        self.extra_headers = extra_headers


class ProvidersConfig(ConfigBase):
    """Configuration for LLM providers."""

    _nested = {
        'anthropic': ProviderConfig,
        'openai': ProviderConfig,
        'openrouter': ProviderConfig,
        'deepseek': ProviderConfig,
        'groq': ProviderConfig,
        'zhipu': ProviderConfig,
        'dashscope': ProviderConfig,
        'vllm': ProviderConfig,
        'gemini': ProviderConfig,
        'moonshot': ProviderConfig,
        'minimax': ProviderConfig,
        'aihubmix': ProviderConfig,
    }

    def __init__(self, anthropic=None, openai=None, openrouter=None,
                 deepseek=None, groq=None, zhipu=None, dashscope=None,
                 vllm=None, gemini=None, moonshot=None, minimax=None,
                 aihubmix=None):
        self.anthropic = anthropic if anthropic is not None else ProviderConfig()
        self.openai = openai if openai is not None else ProviderConfig()
        self.openrouter = openrouter if openrouter is not None else ProviderConfig()
        self.deepseek = deepseek if deepseek is not None else ProviderConfig()
        self.groq = groq if groq is not None else ProviderConfig()
        self.zhipu = zhipu if zhipu is not None else ProviderConfig()
        self.dashscope = dashscope if dashscope is not None else ProviderConfig()
        self.vllm = vllm if vllm is not None else ProviderConfig()
        self.gemini = gemini if gemini is not None else ProviderConfig()
        self.moonshot = moonshot if moonshot is not None else ProviderConfig()
        self.minimax = minimax if minimax is not None else ProviderConfig()
        self.aihubmix = aihubmix if aihubmix is not None else ProviderConfig()


# ---------------------------------------------------------------------------
# Gateway / Tools configuration
# ---------------------------------------------------------------------------

class GatewayConfig(ConfigBase):
    """Gateway/server configuration."""

    def __init__(self, host="0.0.0.0", port=18790):
        self.host = host
        self.port = port


class WebSearchConfig(ConfigBase):
    """Web search tool configuration."""

    def __init__(self, api_key="", max_results=5):
        self.api_key = api_key
        self.max_results = max_results


class WebToolsConfig(ConfigBase):
    """Web tools configuration."""

    _nested = {'search': WebSearchConfig}

    def __init__(self, search=None):
        self.search = search if search is not None else WebSearchConfig()


class ExecToolConfig(ConfigBase):
    """Shell exec tool configuration."""

    def __init__(self, timeout=60):
        self.timeout = timeout


class ToolsConfig(ConfigBase):
    """Tools configuration."""

    _nested = {'web': WebToolsConfig, 'exec': ExecToolConfig}

    def __init__(self, web=None, restrict_to_workspace=False, **kwargs):
        self.web = web if web is not None else WebToolsConfig()
        # 'exec' shadows the builtin; accept via **kwargs for safety
        exec_val = kwargs.get('exec')
        self.exec = exec_val if exec_val is not None else ExecToolConfig()
        self.restrict_to_workspace = restrict_to_workspace


# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------

class Config(ConfigBase):
    """Root configuration for nanobot."""

    _nested = {
        'agents': AgentsConfig,
        'channels': ChannelsConfig,
        'providers': ProvidersConfig,
        'gateway': GatewayConfig,
        'tools': ToolsConfig,
    }

    def __init__(self, agents=None, channels=None, providers=None,
                 gateway=None, tools=None):
        self.agents = agents if agents is not None else AgentsConfig()
        self.channels = channels if channels is not None else ChannelsConfig()
        self.providers = providers if providers is not None else ProvidersConfig()
        self.gateway = gateway if gateway is not None else GatewayConfig()
        self.tools = tools if tools is not None else ToolsConfig()

    @property
    def workspace_path(self):
        """Get expanded workspace path (string, no pathlib)."""
        path = self.agents.defaults.workspace
        if path.startswith('~'):
            try:
                import os
                home = os.getenv('HOME') or '/root'
            except (ImportError, AttributeError):
                home = '/root'
            path = home + path[1:]
        return path

    def _match_provider(self, model=None):
        """Match provider config and its registry name. Returns (config, spec_name)."""
        from nanobot.providers.registry import PROVIDERS
        model_lower = (model or self.agents.defaults.model).lower()

        # Match by keyword (order follows PROVIDERS registry)
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and any(kw in model_lower for kw in spec.keywords) and p.api_key:
                return p, spec.name

        # Fallback: first provider with an api_key
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and p.api_key:
                return p, spec.name
        return None, None

    def get_provider(self, model=None):
        """Get matched provider config. Falls back to first available."""
        p, _ = self._match_provider(model)
        return p

    def get_provider_name(self, model=None):
        """Get the registry name of the matched provider."""
        _, name = self._match_provider(model)
        return name

    def get_api_key(self, model=None):
        """Get API key for the given model. Falls back to first available key."""
        p = self.get_provider(model)
        return p.api_key if p else None

    def get_api_base(self, model=None):
        """Get API base URL for the given model."""
        from nanobot.providers.registry import find_by_name
        p, name = self._match_provider(model)
        if p and p.api_base:
            return p.api_base
        if name:
            spec = find_by_name(name)
            if spec and spec.is_gateway and spec.default_api_base:
                return spec.default_api_base
        return None
