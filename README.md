# Signal — AI Research Radar

AI 뉴스, 새 논문, 주요 학회 신호를 매일 모아 SQLite에 보관하고 정적 웹 대시보드로 발행하는 로컬 우선 프로젝트입니다. API 키나 별도 서버가 없어도 동작하도록 Python 표준 라이브러리만 사용합니다.

## 포함된 기능

- arXiv 핵심 5개 분야의 최신 논문과 12개 공식 세부 카테고리의 2022년 이후 연간 등록 수 수집
- OpenReview의 ICLR, ICML, NeurIPS, ACL 공개 논문 수집
- 연구소·기업의 공식 RSS/Atom 뉴스 수집
- URL/외부 ID 기준 중복 제거와 SQLite 누적 보관
- 7개 1차 분야와 30여 개 2차 연구 주제의 계층형 분류 및 분류 근거 보관
- 최근 7일과 이전 21일을 비교한 2차 연구 주제 모멘텀 분석
- 28일 수집량, 5개년 분야별 arXiv 등록 수·증감, 자료·소스 구성, 1차→2차 분류 지도를 제공하는 통계 탭
- 분야·세부 주제 필터, 한국어 개요·연구 동기·핵심 기여, 중요도·키워드 중심의 카드 뉴스와 기기별 읽음·별표 관리
- 2차 연구 주제별 논문 수·비중·분류 신뢰도와 현재 표본의 집중·저신호 영역을 보여주는 세부 인사이트
- 12개 대표 학회의 논문 접수 시작·마감·리뷰·최종 발표를 한 축에 비교하는 통합 타임라인
- 오늘의 브리핑, 카드 뉴스, 통계, 검색·아카이브, 학회 레이더, 소스 상태 탭
- Windows 작업 스케줄러 등록 스크립트

## 바로 실행하기

```powershell
python dashboard.py update
python dashboard.py serve
```

브라우저에서 `http://127.0.0.1:8765`를 열면 됩니다. 대시보드 파일만 확인할 때는 `web/index.html`을 직접 열어도 검색과 탭 이동이 작동합니다.

## 매일 자동 갱신

기본 시각인 오전 7시 30분에 등록하려면 PowerShell에서 다음을 실행합니다.

```powershell
.\scripts\register_daily_task.ps1
```

다른 시각을 쓰려면 `-Time`에 24시간 형식을 전달합니다.

```powershell
.\scripts\register_daily_task.ps1 -Time "06:45"
```

등록된 작업은 `scripts/update_dashboard.ps1`을 호출하며 실행 기록은 `logs/`에 남습니다. 작업 스케줄러에서 `AI Research Dashboard - Daily Update`라는 이름으로 확인하거나 중지할 수 있습니다.

## 명령어

```text
python dashboard.py init
python dashboard.py collect --max-items 50
python dashboard.py render --item-limit 300
python dashboard.py update
python dashboard.py search "multimodal agent"
python dashboard.py serve --port 8765
```

수집 소스와 학회 목록은 `config/sources.json`에서 추가하거나 비활성화할 수 있습니다. 개별 소스 오류는 전체 갱신을 멈추지 않으며 대시보드의 `수집 소스` 탭에 상태로 표시됩니다.

OpenReview 공개 API가 브라우저 챌린지를 요구하는 시점에는 해당 소스가 `오류`로 표시될 수 있습니다. 이 경우에도 arXiv, 공식 연구 블로그, 학회 블로그 수집과 대시보드 생성은 정상적으로 계속되며, 다음 실행 때 자동으로 다시 시도합니다.

## 데이터 구조

- `data/ai_research.db`: 원본 메타데이터와 수집 실행 기록
- `data/dashboard.json`: 다른 도구에서도 쓸 수 있는 렌더링 결과
- `web/data.js`: 파일로 직접 열 수 있는 브라우저용 데이터
- `web/`: HTML, CSS, JavaScript 대시보드

SQLite의 `item_classifications` 테이블에는 자료별 1차·2차 분류, 신뢰도, 매칭 근거가 저장됩니다. 현재 분석은 재현 가능한 가중 키워드 방식이며, 이후 요약 모델이나 임베딩 검색을 추가해도 수집·DB·표시 계층이 분리되어 있어 기존 데이터는 그대로 유지할 수 있습니다.

카드의 한국어 분석은 별도 유료 API 없이 제목·초록의 연구 신호와 계층형 분류를 조합해 개요, 연구 동기, 핵심 기여로 나누어 생성합니다. 따라서 번역문이 아니라 연구 질문과 기여 유형을 빠르게 파악하기 위한 구조화된 한국어 다이제스트입니다. 연도별 통계는 arXiv의 공식 연도별 카테고리 목록에 표시되는 12개 분야의 등록 수를 사용합니다. 현재 연도는 연중 누적이며 교차 등록 논문은 여러 카테고리에 중복 집계될 수 있습니다.

## GitHub Pages로 공개하기

이 프로젝트는 별도의 API 키 없이 GitHub Pages와 GitHub Actions만으로 운영할 수 있습니다. `web/`만 웹사이트로 공개되며, GitHub Actions가 매일 오전 7시 30분(Asia/Seoul)에 Python 수집기를 실행하고 SQLite와 정적 데이터를 갱신한 뒤 새 화면을 배포합니다.

1. GitHub에 빈 저장소를 만들고 이 폴더를 `main` 브랜치로 푸시합니다.
2. 저장소의 **Settings → Pages → Build and deployment → Source**에서 **GitHub Actions**를 선택합니다.
3. **Actions** 탭의 `Update data and deploy GitHub Pages`를 한 번 수동 실행하거나 `main`에 새 커밋을 푸시합니다.
4. 배포가 끝나면 `https://<GitHub 사용자명>.github.io/<저장소명>/`에서 접속합니다.

배포 워크플로는 `.github/workflows/deploy-pages.yml`에 있습니다. 수동 실행 시에도 최신 데이터를 수집하며, 코드만 푸시했을 때는 저장된 `web/` 파일을 즉시 배포합니다. 예약 실행이 만든 데이터 변경은 GitHub Actions 봇이 저장소에 자동 커밋합니다.

### 커스텀 도메인

첫 배포 후 GitHub 저장소의 **Settings → Pages → Custom domain**에 보유한 도메인을 입력하고, 도메인 업체의 DNS 설정에서 GitHub가 안내하는 레코드를 추가하면 됩니다. 도메인이 확정되기 전에는 `web/CNAME` 파일을 만들지 않아도 됩니다.

### 공개 범위와 상태 저장

- 웹 배포에는 `web/` 폴더만 포함됩니다.
- API 키나 비밀번호는 저장소에 커밋하지 않습니다. 현재 수집원은 인증 키가 필요 없습니다.
- 읽음과 별표는 브라우저 `localStorage`에 저장되므로 PC와 모바일 사이에서 자동 동기화되지 않습니다.
- GitHub Free에서 Pages를 무료로 쓰려면 일반적으로 공개 저장소로 시작하는 편이 가장 단순합니다. SQLite에는 공개 논문·뉴스 메타데이터만 저장됩니다.
