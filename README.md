# naver-news-crawler
설정한 기간에 따라 네이버 뉴스 경제면 헤드라인 데이터를 웹크롤링하여 문장을 형태소로 가공한 다음, 등장 빈도수를 시각화한 워드 클라우드 생성 알고리즘.
웹크롤링 데이터를 이미지로 가공하는 과정에서 Java script를 사용하기 때문에 프로그램을 정상적으로 구동하기 위해선 JDK 파일도 같이 컴퓨터에 설치해야 하니 참고 바랍니다.

✅ 필요한 다운로드 파일 및 설정
1️⃣ Python 패키지 (pip 설치 필요)
아래 패키지들이 naver_news_crawler_worldcloud.py 코드에서 사용됨.
pip install requests beautifulsoup4 wordcloud matplotlib konlpy
추가적으로 lxml, concurrent.futures, collections 등은 기본적으로 Python에 포함됨.

2️⃣ 크롬 드라이버 (선택 사항)
코드에서는 requests를 사용하여 정적 크롤링을 진행하지만, 만약 네이버 뉴스 페이지 구조가 변경되거나 JavaScript 기반으로 동작하면 Selenium이 필요할 수도 있음.
크롬 드라이버 다운로드: ChromeDriver
Windows 사용자: chromedriver.exe를 다운로드 후, 스크립트와 같은 폴더에 위치
Mac/Linux 사용자: 다운로드 후 실행 권한 부여
chmod +x chromedriver

3️⃣ 한글 폰트 파일 (워드클라우드 생성 시 필요)
코드에서 "C:/Windows/Fonts/malgun.ttf" 폰트를 사용하도록 되어 있음.
👉 Windows 사용자는 기본 포함됨
👉 Mac/Linux 사용자는 한글 폰트를 따로 다운로드 후 경로 변경 필요
예시: font_path="/Library/Fonts/AppleGothic.ttf"

4️⃣ 불용어 리스트 (코드 내장됨, 필요 시 수정 가능)
DEFAULT_STOPWORDS에 불용어 사전이 포함되어 있으며,
EXCLUDED_KEYWORDS는 필터링에서 제외할 단어 목록임.
👉 필요하면 naver_news_crawler_worldcloud.py에서 수정 가능.

✅ 최종적으로 필요한 파일 목록
파일명	설명
naver_news_crawler_worldcloud.py	네이버 경제 뉴스 크롤링 및 워드클라우드 생성 코드
chromedriver.exe (선택)	Selenium이 필요할 경우
한글 폰트 (malgun.ttf 또는 AppleGothic.ttf)	워드클라우드 시각화용 폰트
데이터 CSV (자동 생성됨)	크롤링한 뉴스 헤드라인 저장 (필요 시 CSV 저장 기능 추가 가능)
