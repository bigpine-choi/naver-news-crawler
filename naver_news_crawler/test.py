import requests
from bs4 import BeautifulSoup
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from konlpy.tag import Okt
from collections import Counter
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import logging

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ 기본 설정값
BASE_URL = "https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1=101&date={date}&page={page}"

# ✅ 불용어 리스트
DEFAULT_STOPWORDS = {
    "기자", "이", "그", "것", "저", "등", "및", "중", "대한", "이번", "관련",
    "수", "더", "로", "위", "대해", "등의", "지난", "오늘", "내일", "올해",
    "경우", "새로운", "뉴스", "경제", "보도", "대한민국", "정부", "금융", "시장",
    "포토", "한국", "속보", "위해", "중앙", "서울", "대통령", "전국", "사람", "의원"
}

# ✅ 자동 제거에서 복원할 단어 리스트
EXCLUDED_KEYWORDS = {"트럼프"}

# ✅ 특정 날짜의 마지막 페이지 번호를 가져오는 함수
def get_last_page(session, date):
    """ 특정 날짜의 마지막 페이지 번호를 가져오는 함수 """
    url = BASE_URL.format(date=date, page=1)
    try:
        response = session.get(url, timeout=5)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        # ✅ 마지막 페이지 번호 찾기
        page_numbers = [
            int(a.get_text(strip=True)) for a in soup.select(".paging a")
            if a.get_text(strip=True).isdigit()
        ]
        return max(page_numbers) if page_numbers else 5  # ✅ 기본값 5페이지

    except requests.RequestException as e:
        logging.error(f"❌ 페이지 수 확인 실패 ({date}): {e}")
        return 5  # ✅ 오류 발생 시 기본 5페이지

# ✅ 네이버 경제 뉴스 크롤링 함수 (병렬 처리)
def fetch_news(session, date, page):
    """ 특정 날짜와 페이지의 뉴스 제목을 가져오는 함수 """
    url = BASE_URL.format(date=date, page=page)
    try:
        response = session.get(url, timeout=5)  # ✅ 5초 타임아웃 추가
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")

        headlines = [
            headline.get_text(strip=True)
            for headline in soup.select(".list_body.newsflash_body li dt:not(.photo) a")
        ]

        return headlines if headlines else None

    except requests.Timeout:
        logging.error(f"⏳ 타임아웃 발생 ({date}, 페이지 {page})")
        return None
    except requests.RequestException as e:
        logging.error(f"❌ 요청 실패 ({date}, 페이지 {page}): {e}")
        return None

# ✅ 기간별 크롤링 (동적 페이지 크롤링)
def get_news_titles_by_date(start_date, end_date):
    """ 특정 기간 동안의 네이버 경제 뉴스 기사 제목을 크롤링 (동적 페이지 처리) """
    news_titles = []
    max_workers = min(10, os.cpu_count() or 4)

    with requests.Session() as session:
        session.headers.update({"User-Agent": "Mozilla/5.0"})

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            tasks = []
            date_cursor = start_date

            while date_cursor <= end_date:
                formatted_date = date_cursor.strftime("%Y%m%d")
                logging.info(f"📅 {formatted_date} 뉴스 크롤링 중...")

                # ✅ 첫 페이지 요청 및 마지막 페이지 확인
                first_page_titles = fetch_news(session, formatted_date, 1)
                if first_page_titles:
                    news_titles.extend(first_page_titles)

                    # ✅ 해당 날짜의 마지막 페이지 번호 가져오기
                    last_page = get_last_page(session, formatted_date)

                    # ✅ 2페이지부터 마지막 페이지까지 크롤링 (병렬 처리)
                    tasks += [executor.submit(fetch_news, session, formatted_date, page) for page in range(2, last_page + 1)]

                date_cursor += timedelta(days=1)

            # ✅ 병렬 요청 결과 처리
            for future in as_completed(tasks):
                result = future.result()
                if result:
                    news_titles.extend(result)

    return list(set(news_titles))  # ✅ 중복 제거

# ✅ 워드 클라우드 생성 함수 (빈도수 높은 단어 자동 제거 추가, 예외 처리)
def create_wordcloud(news_titles, top_n_stopwords=5):
    """ 크롤링한 뉴스 제목을 활용하여 가독성 높은 워드 클라우드를 생성하는 함수 """
    okt = Okt()

    # ✅ 명사 추출 + 불용어 제거 + 한 글자 단어 제외
    words = [noun for title in news_titles for noun in okt.nouns(title)
             if noun not in DEFAULT_STOPWORDS and len(noun) > 1]

    word_freq = Counter(words)

    # ✅ 상위 N개 단어 자동 불용어 추가 (단, EXCLUDED_KEYWORDS는 제외)
    common_words = {word for word, _ in word_freq.most_common(top_n_stopwords) if word not in EXCLUDED_KEYWORDS}
    filtered_word_freq = {word: freq for word, freq in word_freq.items() if word not in common_words}

    logging.info(f"🛑 자동으로 제외된 상위 {top_n_stopwords}개 단어 (단, {EXCLUDED_KEYWORDS} 제외): {common_words}")

    # ✅ 개선된 워드 클라우드 설정
    wordcloud = WordCloud(
        font_path="C:/Windows/Fonts/malgun.ttf",
        background_color="white",
        width=1000,
        height=600,
        max_words=150,
        colormap="Dark2",
        prefer_horizontal=1.0,
        relative_scaling=0.5
    ).generate_from_frequencies(filtered_word_freq)

    # ✅ 워드 클라우드 출력
    plt.figure(figsize=(12, 6))
    plt.imshow(wordcloud, interpolation="bilinear")
    plt.axis("off")
    plt.show()

# ✅ 실행 코드
if __name__ == "__main__":
    start_date = datetime(2025, 1, 1)
    end_date = datetime(2025, 2, 7)

    news_titles = get_news_titles_by_date(start_date, end_date)

    logging.info(f"\n📢 네이버 경제 뉴스 헤드라인 ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}):")
    print("\n".join(f"{i + 1}. {title}" for i, title in enumerate(news_titles[:20])))

    create_wordcloud(news_titles)