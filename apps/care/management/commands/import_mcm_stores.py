import csv
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.core.management.base import (
    BaseCommand,
    CommandError,
)

from apps.care.models import Store


KAKAO_ADDRESS_SEARCH_URL = (
    "https://dapi.kakao.com/v2/local/search/address.json"
)
KAKAO_KEYWORD_SEARCH_URL = (
    "https://dapi.kakao.com/v2/local/search/keyword.json"
)

MAX_GEOCODING_RETRIES = 3
GEOCODING_REQUEST_INTERVAL = 0.15


class KakaoGeocodingError(Exception):
    def __init__(
        self,
        status_code=None,
        error_type="",
        message="",
        response_body="",
    ):
        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        self.response_body = response_body

        super().__init__(
            f"{status_code} / {error_type} / {message}"
        )


def clean(value):
    if value is None:
        return ""

    return str(value).strip()


def parse_kakao_error(error_body):
    try:
        payload = json.loads(error_body)
    except (json.JSONDecodeError, TypeError):
        return "", error_body

    error_type = clean(
        payload.get("errorType")
        or payload.get("type")
        or payload.get("code")
    )
    message = clean(
        payload.get("message")
        or payload.get("msg")
        or error_body
    )

    return error_type, message


def build_authorization_error_message(error):
    message_lower = error.message.lower()

    if (
        "open_map_and_local" in message_lower
        or "disabled" in message_lower
    ):
        return (
            "AURA 앱에서 카카오맵·로컬 API가 비활성화돼 있습니다.\n"
            "Kakao Developers → 내 애플리케이션 → AURA → "
            "제품 설정 → 카카오맵에서 활성화 설정을 ON으로 "
            "변경한 뒤 다시 실행해 주세요.\n"
            f"Kakao 응답: {error.response_body}"
        )

    if error.status_code == 401:
        return (
            "Kakao REST API 키 인증에 실패했습니다.\n"
            ".env의 KAKAO_REST_API_KEY에 JavaScript 키가 아닌 "
            "REST API 키가 입력됐는지 확인해 주세요.\n"
            f"Kakao 응답: {error.response_body}"
        )

    if error.status_code == 403:
        return (
            "Kakao API 접근 권한이 거부됐습니다.\n"
            "카카오맵·로컬 API 활성화 여부와 REST API 키의 "
            "허용 IP 설정을 확인해 주세요.\n"
            f"Kakao 응답: {error.response_body}"
        )

    return (
        f"Kakao 주소 검색 인증 오류: {error.status_code}\n"
        f"Kakao 응답: {error.response_body}"
    )


def request_kakao_local_api(url, query, api_key):
    """
    Kakao Local API를 호출하고 JSON 응답을 반환합니다.

    429 및 Kakao 서버의 일시적 오류는 최대 3번 재시도합니다.
    인증 및 권한 오류는 즉시 예외를 발생시킵니다.
    """
    query_string = urlencode({"query": query})
    request_url = f"{url}?{query_string}"

    request = Request(
        request_url,
        headers={
            "Authorization": f"KakaoAK {api_key}",
            "User-Agent": "AURA-BE/1.0",
            "Accept": "application/json",
        },
        method="GET",
    )

    for attempt in range(1, MAX_GEOCODING_RETRIES + 1):
        try:
            with urlopen(request, timeout=10) as response:
                response_body = response.read().decode("utf-8")
                return json.loads(response_body)

        except HTTPError as exc:
            error_body = exc.read().decode(
                "utf-8",
                errors="replace",
            )
            error_type, message = parse_kakao_error(error_body)

            error = KakaoGeocodingError(
                status_code=exc.code,
                error_type=error_type,
                message=message,
                response_body=error_body,
            )

            if exc.code in (401, 403):
                raise error from exc

            if exc.code == 429 or 500 <= exc.code < 600:
                if attempt < MAX_GEOCODING_RETRIES:
                    time.sleep(attempt)
                    continue

            raise error from exc

        except URLError as exc:
            if attempt < MAX_GEOCODING_RETRIES:
                time.sleep(attempt)
                continue

            raise KakaoGeocodingError(
                message=f"연결 오류: {exc.reason}",
                response_body=str(exc.reason),
            ) from exc

        except json.JSONDecodeError as exc:
            raise KakaoGeocodingError(
                message="Kakao 응답을 JSON으로 해석할 수 없습니다.",
                response_body=str(exc),
            ) from exc

    return {}


def extract_coordinates(payload):
    documents = payload.get("documents", [])

    if not documents:
        return None, None

    first_result = documents[0]

    latitude = clean(first_result.get("y"))
    longitude = clean(first_result.get("x"))

    if not latitude or not longitude:
        return None, None

    return latitude, longitude


def geocode_address(address, api_key):
    """
    Kakao 주소 검색 API를 사용해 주소를 좌표로 변환합니다.
    """
    payload = request_kakao_local_api(
        KAKAO_ADDRESS_SEARCH_URL,
        address,
        api_key,
    )

    return extract_coordinates(payload)


def geocode_keyword(keyword, api_key):
    """
    주소 검색에 실패한 경우 매장명 기반 키워드 검색을 수행합니다.
    """
    payload = request_kakao_local_api(
        KAKAO_KEYWORD_SEARCH_URL,
        keyword,
        api_key,
    )

    return extract_coordinates(payload)


class Command(BaseCommand):
    help = (
        "MCM 매장 CSV를 읽어 중복을 제거하고 "
        "Store 테이블에 등록합니다."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_path",
            type=str,
            help="mcm_stores.csv 파일 경로",
        )
        parser.add_argument(
            "--geocode",
            action="store_true",
            help=(
                "Kakao Local API로 매장 주소의 "
                "위도·경도를 생성합니다."
            ),
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help=(
                "기존 MCM 매장 데이터를 삭제한 뒤 "
                "다시 등록합니다."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "DB에 저장하지 않고 처리 결과만 확인합니다. "
                "--geocode와 함께 사용하면 Kakao API는 호출합니다."
            ),
        )
        parser.add_argument(
            "--skip-geocode-errors",
            action="store_true",
            help=(
                "개별 좌표 검색이 실패해도 좌표 없이 "
                "매장 데이터를 저장합니다. "
                "인증 및 권한 오류에는 적용되지 않습니다."
            ),
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"]).expanduser()

        if not csv_path.exists():
            raise CommandError(
                f"CSV 파일을 찾을 수 없습니다: {csv_path}"
            )

        if not csv_path.is_file():
            raise CommandError(
                f"CSV 경로가 파일이 아닙니다: {csv_path}"
            )

        kakao_api_key = clean(
            os.getenv("KAKAO_REST_API_KEY")
        )

        if options["geocode"] and not kakao_api_key:
            raise CommandError(
                "--geocode 사용 시 KAKAO_REST_API_KEY가 필요합니다.\n"
                "manage.py와 같은 위치의 .env 파일을 확인해 주세요."
            )

        with csv_path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as csv_file:
            source_rows = list(csv.DictReader(csv_file))

        if not source_rows:
            raise CommandError(
                "CSV 파일에 매장 데이터가 없습니다."
            )

        selected_rows = self.select_unique_stores(source_rows)

        self.stdout.write(
            f"원본 {len(source_rows)}건, "
            f"중복 제거 후 {len(selected_rows)}건"
        )

        if options["replace"] and not options["dry_run"]:
            deleted_count, _ = Store.objects.filter(
                name__icontains="MCM"
            ).delete()

            self.stdout.write(
                self.style.WARNING(
                    f"기존 MCM 관련 데이터 {deleted_count}건 삭제"
                )
            )

        created_count = 0
        updated_count = 0
        geocoded_count = 0
        coordinate_missing_count = 0
        geocoding_failed_count = 0

        total_count = len(selected_rows)

        for index, row in enumerate(selected_rows, start=1):
            official_store_id = (
                clean(row.get("official_store_id")) or None
            )

            store_name = (
                clean(row.get("official_store_name"))
                or clean(row.get("store_name"))
            )

            official_address = clean(
                row.get("official_address")
            )
            original_address = clean(
                row.get("address")
            )

            # DB에는 공식 주소를 우선 저장합니다.
            address = official_address or original_address

            sido = clean(row.get("sido"))
            sigungu = clean(row.get("sigungu"))

            if not store_name or not address:
                self.stdout.write(
                    self.style.WARNING(
                        f"[{index}/{total_count}] "
                        "매장명 또는 주소가 없어 건너뜁니다."
                    )
                )
                continue

            latitude = None
            longitude = None
            geocode_source = ""

            if options["geocode"]:
                try:
                    (
                        latitude,
                        longitude,
                        geocode_source,
                    ) = self.find_store_coordinates(
                        store_name=store_name,
                        official_address=official_address,
                        original_address=original_address,
                        sido=sido,
                        sigungu=sigungu,
                        api_key=kakao_api_key,
                    )

                except KakaoGeocodingError as error:
                    if error.status_code in (401, 403):
                        raise CommandError(
                            build_authorization_error_message(error)
                        ) from error

                    geocoding_failed_count += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"[좌표 검색 실패] {store_name}: "
                            f"{error}"
                        )
                    )

                    if not options["skip_geocode_errors"]:
                        raise CommandError(
                            f"{store_name} 좌표 검색에 실패했습니다.\n"
                            f"{error.response_body}\n"
                            "실패한 매장을 좌표 없이 저장하려면 "
                            "--skip-geocode-errors를 추가해 주세요."
                        ) from error

                if (
                    latitude is not None
                    and longitude is not None
                ):
                    geocoded_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"[좌표 검색 성공] {store_name}: "
                            f"{geocode_source}"
                        )
                    )
                else:
                    coordinate_missing_count += 1

                    self.stdout.write(
                        self.style.WARNING(
                            f"[좌표 없음] {store_name}: "
                            f"{address}"
                        )
                    )

                time.sleep(GEOCODING_REQUEST_INTERVAL)

            store_values = {
                "name": store_name,
                "address": address,
                "phone": clean(row.get("phone")),
                "sido": sido,
                "sigungu": sigungu,
                "store_type": clean(row.get("store_type")),
                "channel": clean(row.get("channel")),
                "opening_hours": clean(
                    row.get("business_hours")
                ),
                "supports_as": True,
                "source_url": clean(
                    row.get("source_phone_hours")
                ),
            }

            # 새 좌표를 찾은 경우에만 좌표를 갱신합니다.
            # 찾지 못한 경우 기존 DB 좌표는 그대로 유지합니다.
            if (
                latitude is not None
                and longitude is not None
            ):
                store_values["latitude"] = latitude
                store_values["longitude"] = longitude

            if options["dry_run"]:
                coordinate_text = (
                    f"{latitude}, {longitude}"
                    if latitude is not None
                    else "좌표 없음"
                )

                self.stdout.write(
                    f"[DRY RUN {index}/{total_count}] "
                    f"{store_name} / {address} / "
                    f"{coordinate_text}"
                )
                continue

            if official_store_id:
                store, created = Store.objects.update_or_create(
                    official_store_id=official_store_id,
                    defaults=store_values,
                )
            else:
                store, created = Store.objects.update_or_create(
                    name=store_name,
                    address=address,
                    defaults={
                        **store_values,
                        "official_store_id": None,
                    },
                )

            if created:
                created_count += 1
                status = "생성"
            else:
                updated_count += 1
                status = "수정"

            coordinate_text = (
                f"{store.latitude}, {store.longitude}"
                if (
                    store.latitude is not None
                    and store.longitude is not None
                )
                else "좌표 없음"
            )

            self.stdout.write(
                f"[{index}/{total_count}] "
                f"[{status}] {store.name} / "
                f"{coordinate_text}"
            )

        if options["dry_run"]:
            self.stdout.write(
                self.style.SUCCESS(
                    "DRY RUN 완료: DB에는 저장하지 않았습니다."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                "완료: "
                f"생성 {created_count}건, "
                f"수정 {updated_count}건, "
                f"좌표 검색 성공 {geocoded_count}건, "
                f"좌표 없음 {coordinate_missing_count}건, "
                f"좌표 검색 실패 {geocoding_failed_count}건"
            )
        )

    def find_store_coordinates(
        self,
        store_name,
        official_address,
        original_address,
        sido,
        sigungu,
        api_key,
    ):
        """
        다음 순서로 매장 좌표를 검색합니다.

        1. 공식 주소
        2. CSV 원본 주소
        3. 시도 + 시군구 + 매장명 키워드
        4. 매장명 키워드
        """
        address_candidates = []

        for candidate in (
            official_address,
            original_address,
        ):
            candidate = clean(candidate)

            if (
                candidate
                and candidate not in address_candidates
            ):
                address_candidates.append(candidate)

        for address_candidate in address_candidates:
            latitude, longitude = geocode_address(
                address_candidate,
                api_key,
            )

            if (
                latitude is not None
                and longitude is not None
            ):
                return (
                    latitude,
                    longitude,
                    f"주소 검색: {address_candidate}",
                )

            time.sleep(GEOCODING_REQUEST_INTERVAL)

        keyword_candidates = []

        region_keyword = clean(
            f"{sido} {sigungu} {store_name}"
        )
        simple_keyword = clean(store_name)

        for candidate in (
            region_keyword,
            simple_keyword,
        ):
            if (
                candidate
                and candidate not in keyword_candidates
            ):
                keyword_candidates.append(candidate)

        for keyword_candidate in keyword_candidates:
            latitude, longitude = geocode_keyword(
                keyword_candidate,
                api_key,
            )

            if (
                latitude is not None
                and longitude is not None
            ):
                return (
                    latitude,
                    longitude,
                    f"키워드 검색: {keyword_candidate}",
                )

            time.sleep(GEOCODING_REQUEST_INTERVAL)

        return None, None, ""

    def select_unique_stores(self, rows):
        """
        duplicate_group이 같은 행은 하나의 물리 매장으로 처리합니다.

        같은 그룹에서는 공식 매칭 정보, 공식 ID, 주소,
        전화번호 및 영업시간이 가장 잘 갖춰진 행을 선택합니다.
        """
        groups = {}

        for row in rows:
            duplicate_group = clean(
                row.get("duplicate_group")
            )

            if not duplicate_group:
                duplicate_group = (
                    clean(row.get("official_store_id"))
                    or (
                        f"{clean(row.get('store_name'))}|"
                        f"{clean(row.get('address'))}"
                    )
                )

            groups.setdefault(
                duplicate_group,
                [],
            ).append(row)

        selected_rows = []

        for group_rows in groups.values():
            group_rows.sort(
                key=self.row_quality_score,
                reverse=True,
            )
            selected_rows.append(group_rows[0])

        selected_rows.sort(
            key=lambda row: int(
                clean(row.get("seq")) or 0
            )
        )

        return selected_rows

    @staticmethod
    def row_quality_score(row):
        score = 0

        if clean(row.get("match_status")) == "matched":
            score += 100

        if clean(row.get("official_store_id")):
            score += 20

        if clean(row.get("official_store_name")):
            score += 10

        if clean(row.get("official_address")):
            score += 10

        if clean(row.get("phone")):
            score += 5

        if clean(row.get("business_hours")):
            score += 5

        return score