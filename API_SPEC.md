# AURA Backend API Specification

모든 `/api/` 요청은 별도 표기가 없으면 JWT 인증이 필요합니다.

```http
Authorization: Bearer <access_token>
```

## 인증

- `POST /api/auth/register/` — `email`, `password`
- `POST /api/auth/token/` — `email`, `password`
- `POST /api/auth/token/refresh/` — `refresh`

로그인 ID는 이메일입니다. 닉네임은 온보딩 이후 표시 이름으로 사용하며 로그인 ID가 아닙니다.

## 프로필과 온보딩

- `GET /api/me/`
- `PATCH /api/me/`

필수 온보딩 값:

- `nickname`
- `gender`
- `age_range`
- `lifestyle`

선택값:

- `preferred_categories`
- `preferred_brands`
- `min_budget`, `max_budget`
- `phone`, `image`, `marketing_agreed`

`onboarding_completed=true`로 변경하려면 필수값이 모두 있어야 합니다. `membership_tier`는 읽기 전용이며 게시글·댓글 수로 계산합니다.

## 알림

- `GET /api/notifications/`
- `GET /api/notifications/{id}/`
- `PATCH /api/notifications/{id}/` — `{"is_read": true}`

필드: `type`, `title`, `body`, `action_url`, `is_read`, `created_at`

알림 종류는 `CARE`, `MEMBERSHIP`, `EVENT`, `GENERAL`입니다. 본인의 알림만 조회·수정할 수 있습니다.

자동 생성 사건:

- 진단 완료·실패
- 방문 예약 생성·상태 변경
- 멤버십 등급 상승

## 디지털 클로젯

- CRUD: `/api/products/`
- 이미지 CRUD: `/api/product-images/`

상품 필드:

- `name`, `brand`, `category`
- `purchased_at`, `purchase_place`
- `purchase_channel`: `ONLINE` 또는 `OFFLINE`
- `purchase_price`, `memo`
- `image`, `metadata`
- 읽기 전용: `passport_code`, `diagnosis_history`, `service_history`

이미지 `kind`:

- `PRODUCT`
- `RECEIPT`
- `WARRANTY`

수동 등록과 이미지 저장은 지원하지만 OCR 추출은 별도 작업입니다. 다른 사용자의 제품 또는 제품 이미지에는 접근할 수 없습니다.

## 케어 가이드

- `GET /api/care-guides/`
- `GET /api/care-guides/{id}/`
- 북마크: `GET/POST/DELETE /api/care-bookmarks/`

필터:

```http
GET /api/care-guides/?guide_type=POST_PURCHASE&material=가죽&category=bag&season=여름
```

`guide_type`:

- `BASIC` — 기본 관리
- `POST_PURCHASE` — 구매 직후 관리
- `AFTER_CARE` — 사후 케어

게시되지 않았거나 존재하지 않는 가이드는 북마크할 수 없습니다.

## 진단 데이터

- `POST/GET /api/diagnoses/`
- `GET/PATCH/DELETE /api/diagnoses/{id}/`

생성은 `multipart/form-data`로 `product`, `image`를 전송합니다. 본인 상품의 진단만 생성하고 본인 기록만 조회·수정·삭제할 수 있습니다.

필터:

```http
GET /api/diagnoses/?product=3&year=2026
```

결과 단계는 `SAFE`, `CAUTION`, `DANGER`이며 화면 표기는 안전·주의·위험입니다. 실제 이미지 판독과 상태 자동 변경은 별도 CV 작업입니다.

## 공식 케어·방문 데모 흐름

- 매장 조회: `GET /api/stores/`, `GET /api/stores/{id}/`
- 방문 예약: CRUD `/api/visit-reservations/`
- 서비스 요청: CRUD `/api/service-requests/`

방문 예약은 `store`, 선택 `product`, `visit_at`, `purpose`, `contact_name`, `contact_phone`, `request_note`를 저장합니다. 서비스 요청은 본인 상품과 본인 방문 예약만 연결할 수 있습니다.

이는 AURA 내부 데모 흐름이며 실제 브랜드 AS 시스템과 직접 연동하지 않습니다.

## 커뮤니티

### 게시글

CRUD: `/api/posts/`

응답에는 작성자 닉네임·멤버십 등급, 다중 이미지, 댓글, 좋아요 수, 내 좋아요 여부와 상품 태그가 포함됩니다.

상품 태그 입력은 `tagged_products`에 본인 상품 ID 목록을 전송합니다. 표시용 `tagged_product_cards`는 다음 형태입니다.

```json
[
  {
    "id": 3,
    "name": "모노그램 숄더백",
    "brand": "MCM"
  }
]
```

내부 관계 식별을 위한 `id` 외 표시 정보는 제품 이름과 브랜드만 제공합니다.

### 게시글 이미지

CRUD: `/api/post-images/`

`multipart/form-data`로 `post`, `image`, `order`를 전송합니다. 본인 게시글에만 이미지를 추가·수정·삭제할 수 있습니다.

### 댓글과 좋아요

- 댓글 CRUD: `/api/comments/`
- 좋아요 목록·생성·삭제: `/api/post-likes/`

게시글과 댓글은 작성자만 수정·삭제할 수 있고 한 사용자는 같은 게시글에 중복 좋아요할 수 없습니다.

## 현재 별도 작업

- 영수증·보증서 OCR 추출
- AI 챗봇 추천·RAG·방문 준비 카드
- 실제 CV 손상 판독
- 외부 브랜드 AS 연동
- 실제 멤버십 결제
