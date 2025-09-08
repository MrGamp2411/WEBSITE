import os
from wallee.configuration import Configuration
from wallee.api_client import ApiClient
from wallee.api import (
    TransactionServiceApi,
    TransactionPaymentPageServiceApi,
    WebhookEncryptionServiceApi,
)

cfg = Configuration()
cfg.user_id = int(os.getenv("WALLEE_USER_ID", "0"))
cfg.api_secret = os.getenv("WALLEE_API_SECRET", "")
# opzionali:
# cfg.timeout = 30
# cfg.verify_ssl = True

api_client = ApiClient(configuration=cfg)

tx_service = TransactionServiceApi(cfg)
pp_service = TransactionPaymentPageServiceApi(cfg)
whenc_srv = WebhookEncryptionServiceApi(cfg)

space_id = int(os.getenv("WALLEE_SPACE_ID", "0"))
