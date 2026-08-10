# AURA Backend API Specification

기준 브랜치: `backend_soyun`

모든 `/api/` 요청은 별도 표기가 없으면 JWT 인증이 필요하다.

```http
Authorization: Bearer <access_token>
```

## 인증

### 회원가입

`POST /api/auth/register/`

```json
{
  "email": "user@example.com",
  "password": "minimum-8-characters"
}
```

- 로그인 ID는 이메일이다.
- Django 내부 `username`에는 이메일을 동일하게 저장하지만 외부 API 입력으로 받지 않는다.
- 닉네임은 로그인 ID가 아니며 온보딩에서 설정한다.

### 로그인

`POST /api/auth/token/`

```json
{
  "email": "user@example.com",
  "password": "minimum-8-characters"
}
```

응답: `access`, `refresh`

### 토큰 갱신

`POST /api/auth/token/refresh/`

## 프로필 및 온보딩

`GET /api/me/`

`PATCH /api/me/`

주요 필드:

- 필수 온보딩 값: `nickname`, `gender`, `age_range`, `lifestyle`
- 선택값: `preferred_categories`, `preferred_brands`, `min_budget`, `max_budget`
- 기타: `phone`, `image`, `marketing_agreed`, `onboarding_completed`
- 읽기 전용: `email`, `membership_tier`

`onboarding_completed=true`로 저장하려면 필수 온보딩 값이 모두 있어야 한다. 모든 값은 이후 `PATCH /api/me/`로 수정할 수 있다.

## 멤버십

포인트와 결제 기능은 없다. 등급은 작성한 게시글 수와 댓글 수를 각각 계산해 자동 산정한다.

| 등급 | 게시글 수 | 댓글 수 |
|---|---:|---:|
| AURA Silver | 기본 | 기본 |
| AURA Gold | 50 이상 | 50 이상 |
| AURA Platinum | 100 이상 | 100 이상 |
| AURA Diamond | 200 이상 | 200 이상 |

두 조건을 모두 충족해야 해당 등급이 된다.

## 알림

- 목록: `GET /api/notifications/`
- 상세: `GET /api/notifications/{id}/`
- 읽음 처리: `PATCH /api/notifications/{id}/` with `{"is_read": true}`

필드:

- `type`: `CARE`, `MEMBERSHIP`, `EVENT`, `GENERAL`
- `title`, `body`
- `action_url`: 알림 클릭 후 이동할 앱 결과 화면 경로
- `is_read`, `created_at`

본인의 알림만 조회·수정할 수 있다.

## 디지털 클로젯

- CRUD: `/api/products/`
- 이미지 CRUD: `/api/product-images/`

상품 주요 필드:

- `name`, `brand`, `category`
- `purchased_at`, `purchase_place`, `purchase_channel`, `memo`
- `image`, `metadata`
- 읽기 전용 `passport_code`, `diagnosis_history`

`passport_code`는 서버가 자동 생성한다.

상품 이미지 `kind`:

- `PRODUCT`
- `RECEIPT`
- `WARRANTY`

OCR 추출은 이 API의 범위가 아니다.

## 진단

- 생성/목록: `POST/GET /api/diagnoses/`
- 상세/수정/삭제: `GET/PATCH/DELETE /api/diagnoses/{id}/`

생성 요청은 `multipart/form-data`로 `product`, `image`를 전송한다.

사용자는 본인 상품의 진단만 생성하고 본인 진단만 조회·수정·삭제할 수 있다. 사용자가 수정할 수 있는 값은 입력 이미지와 연결 상품이며, AI/CV 결과 필드는 읽기 전용이다.

목록 필터:

```http
GET /api/diagnoses/?product=3&year=2026
```

결과 저장 필드:

- `status`: `PENDING`, `DONE`, `FAILED`
- `condition_level`: `SAFE`, `CAUTION`, `DANGER`
- `damage_type`, `damage_description`, `care_suggestion`
- `damage_location`, `result`

실제 CV 판독과 자동 상태 전환은 범위 밖이다.

## 케어 가이드

- 목록/상세: `GET /api/care-guides/`, `GET /api/care-guides/{id}/`
- 북마크: `/api/care-bookmarks/`

필터: `material`, `category`, `season`

공식 출처는 `source_name`, `source_url`로 제공한다.

## 커뮤니티

### 게시글

CRUD: `/api/posts/`

응답에는 다음 정보가 포함된다.

- `author_nickname`
- `author_membership_tier`
- `tagged_products`, `tagged_product_cards`
- `images`
- `comments`, `like_count`, `liked_by_me`

본인이 소유한 클로젯 상품만 게시글에 태그할 수 있다. 게시글 수정·삭제는 작성자만 가능하다.

### 다중 이미지

CRUD: `/api/post-images/`

각 이미지를 `multipart/form-data`로 `post`, `image`, `order`와 함께 등록한다. 한 게시글에 여러 번 호출해 여러 이미지를 추가할 수 있다.

### 댓글

CRUD: `/api/comments/`

생성 시 `post`, `body`를 전송한다. 댓글 응답에도 작성자 닉네임과 멤버십 등급이 포함된다. 수정·삭제는 작성자만 가능하다.

### 좋아요

- 생성/목록/삭제: `/api/post-likes/`
- 같은 사용자는 같은 게시글에 중복 좋아요를 할 수 없다.

## 이번 범위에서 제외

- 실제 AI/RAG 답변 품질
- 실제 CV 손상 판독과 자동 완료 처리
- 실제 OCR 추출
- AS·방문 예약·공식 센터 기능 보완
- 실제 멤버십 결제
