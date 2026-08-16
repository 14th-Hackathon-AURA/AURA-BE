import os
import re

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential


KNOWN_BRANDS = [
    "MCM",
    "LOUIS VUITTON",
    "GUCCI",
    "CHANEL",
    "PRADA",
    "BURBERRY",
    "DIOR",
    "CELINE",
    "HERMES",
    "COACH",
]


def get_document_client():
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    if not endpoint or not key:
        raise RuntimeError(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT 또는 "
            "AZURE_DOCUMENT_INTELLIGENCE_KEY가 없습니다."
        )

    return DocumentIntelligenceClient(
        endpoint=endpoint,
        credential=AzureKeyCredential(key),
    )


def get_field_value(field, attribute):
    if not field:
        return None

    value = getattr(field, attribute, None)

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return value


def get_currency_amount(field):
    if not field:
        return None

    currency = getattr(field, "value_currency", None)
    amount = getattr(currency, "amount", None)

    if amount is None:
        return None

    return int(amount)


def find_brand(text):
    upper_text = (text or "").upper()

    for brand in KNOWN_BRANDS:
        if brand in upper_text:
            return brand

    return None


def extract_receipt_information(file_bytes):
    """
    영수증용 Azure 사전 학습 모델.
    별도 AI 학습 없이 prebuilt-receipt를 사용합니다.
    """
    client = get_document_client()

    poller = client.begin_analyze_document(
        "prebuilt-receipt",
        AnalyzeDocumentRequest(bytes_source=file_bytes),
    )
    result = poller.result()

    if not result.documents:
        return {
            "brand": None,
            "name": None,
            "purchased_at": None,
            "purchase_place": None,
            "purchase_price": None,
        }

    document = result.documents[0]
    fields = document.fields
    raw_text = result.content or ""

    product_name = None
    items = fields.get("Items")

    if items and items.value_array:
        first_item = items.value_array[0]
        item_fields = first_item.value_object or {}

        product_name = get_field_value(
            item_fields.get("Description"),
            "value_string",
        )

    return {
        "brand": find_brand(raw_text),
        "name": product_name,
        "purchased_at": get_field_value(
            fields.get("TransactionDate"),
            "value_date",
        ),
        "purchase_place": get_field_value(
            fields.get("MerchantName"),
            "value_string",
        ),
        "purchase_price": get_currency_amount(fields.get("Total")),
    }


def extract_warranty_information(file_bytes):
    """
    보증서는 양식이 제각각이라 prebuilt-layout으로 텍스트를 읽습니다.
    확실히 찾지 못한 항목은 None으로 반환해 사용자가 직접 입력합니다.
    """
    client = get_document_client()

    poller = client.begin_analyze_document(
        "prebuilt-layout",
        AnalyzeDocumentRequest(bytes_source=file_bytes),
    )
    result = poller.result()

    raw_text = result.content or ""

    date_match = re.search(
        r"\b(20\d{2})[.\-/년\s]+(\d{1,2})[.\-/월\s]+(\d{1,2})",
        raw_text,
    )

    purchased_at = None

    if date_match:
        year, month, day = date_match.groups()
        purchased_at = f"{year}-{int(month):02d}-{int(day):02d}"

    return {
        "brand": find_brand(raw_text),
        "name": None,
        "purchased_at": purchased_at,
        "purchase_place": None,
        "purchase_price": None,
    }