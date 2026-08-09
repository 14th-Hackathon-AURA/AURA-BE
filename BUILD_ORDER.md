# 직접 구현하는 순서

## 1. 파일을 만들기 전

프로젝트 생성 뒤 `config/settings.py`에서 `rest_framework`, `corsheaders`, `apps.accounts`, `apps.catalog`, `apps.care`, `apps.community`, `apps.ai`를 `INSTALLED_APPS`에 등록한다. `MEDIA_URL`, `MEDIA_ROOT`, JWT 설정도 넣는다.

## 2. 앱별 작성 순서

각 앱마다 반드시 아래 순서를 지킨다. 한 앱의 `models.py`를 먼저 완성한 후에 serializer/view를 쓰는 이유는 serializer가 모델을 import하기 때문이다.

1. `accounts/models.py` → `serializers.py` → `views.py`
2. `catalog/models.py` → `serializers.py` → `views.py`
3. `care/models.py` → `serializers.py` → `views.py`
4. `community/models.py` → `serializers.py` → `views.py`
5. `ai/models.py` → `serializers.py` → `views.py`
6. 마지막으로 `config/urls.py`를 이 폴더의 파일로 교체한다.

각 단계는 이 폴더의 같은 경로 파일을 통째로 복사해 넣으면 된다. 직접 타이핑한다면 한 파일을 저장한 뒤 다음 파일로 넘어간다.

## 3. DB 반영

모든 모델을 붙여넣은 뒤 한 번만 아래를 실행한다.

```bash
python manage.py makemigrations accounts catalog care community ai
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

모델을 수정할 때마다 `makemigrations`와 `migrate`를 다시 실행한다. migration 파일은 Git에 커밋한다.

## 4. 화면별 연결 API

| 화면 | API |
|---|---|
| 회원가입/로그인 | `POST /api/auth/register/`, `POST /api/auth/token/` |
| 온보딩/마이페이지 | `GET/PATCH /api/me/`, `GET /api/notifications/` |
| 디지털 클로젯 | `/api/products/`, `/api/product-images/` |
| 케어 가이드 | `GET /api/care-guides/`, `/api/care-bookmarks/` |
| AI 채팅 | `POST /api/ai/chat/`, `GET /api/ai/chat-sessions/` |
| 진단 | `/api/diagnoses/`, `POST /api/ai/care-recommendations/` |
| 매장/방문 카드 | `GET /api/stores/`, `/api/visit-reservations/` |
| AS 접수 | `/api/service-requests/` |
| 커뮤니티 | `/api/posts/`, `/api/comments/?post=<게시글ID>`, `/api/post-likes/` |

## 5. 지금 코드는 MVP 범위

AI 사진 진단의 `Diagnosis.status`는 처음에는 `PENDING`으로 저장된다. 실제 이미지 모델 또는 작업 큐(Celery)를 붙여 완료 시 `DONE`과 `result` JSON을 업데이트해야 한다. 관리자 화면에서 Store와 CareGuide 데이터를 우선 등록하면 프론트 화면을 바로 연결할 수 있다.
