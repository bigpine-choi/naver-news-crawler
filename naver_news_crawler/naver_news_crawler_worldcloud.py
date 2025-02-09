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
import time

# ✅ 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# ✅ 기본 설정값
BASE_URL = "https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1=101&date={date}&page={page}"

# ✅ 불용어 리스트
DEFAULT_STOPWORDS = {
    "기자", "지난해", "지원", "기업", "최대", "연휴", "역대", "사업", "대한", "이번", "관련", "대해", "등의", "지난", "오늘",
    "내일", "올해", "경우", "새로운", "뉴스", "경제", "보도", "대한민국", "정부", "금융", "시장", "포토", "한국", "속보", "위해",
    "작년", "투자", "개월", "브랜드"
}

# ✅ 자동 제거에서 복원할 단어 리스트
EXCLUDED_KEYWORDS = {"트럼프", "삼성", "전쟁", "시크", "관세", "하이닉스", "아파트", "세종", "대왕고래", "인하", "접속", "차단", "외교", "산업부", "대출", "올트먼", "제주항공", "고려아연"}

# ✅ 특정 날짜의 마지막 페이지 번호를 가져오는 함수
def get_last_page(session, date):
    """ 특정 날짜의 마지막 페이지 번호를 가져오는 함수 """
    url = BASE_URL.format(date=date, page=1)
    try:
        response = session.get(url, timeout=5)  # ✅ 5초 제한
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

# ✅ 네이버 경제 뉴스 크롤링 함수 (에러 발생 시 재시도 기능 추가)
def fetch_news(session, date, page, retries=3):
    """ 특정 날짜와 페이지의 뉴스 제목을 가져오는 함수 (최대 3번 재시도) """
    url = BASE_URL.format(date=date, page=page)
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=5)  # ✅ 5초 타임아웃
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")

            headlines = [
                headline.get_text(strip=True)
                for headline in soup.select(".list_body.newsflash_body li dt:not(.photo) a")
            ]

            return headlines if headlines else None

        except requests.Timeout:
            logging.warning(f"⏳ 타임아웃 발생 ({date}, 페이지 {page}) - 재시도 {attempt + 1}/{retries}")
        except requests.RequestException as e:
            logging.error(f"❌ 요청 실패 ({date}, 페이지 {page}) - 재시도 {attempt + 1}/{retries}: {e}")

        time.sleep(1)  # ✅ 재시도 전 1초 대기

    logging.error(f"🚨 최대 재시도 횟수 초과: {date}, 페이지 {page}")
    return None

# ✅ 기간별 크롤링 (동적 페이지 크롤링)
def get_news_titles_by_date(start_date, end_date):
    """ 특정 기간 동안의 네이버 경제 뉴스 기사 제목을 크롤링 (동적 페이지 처리) """
    news_titles = set()  # ✅ 중복 제거를 위해 set 사용
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
                    news_titles.update(first_page_titles)

                    # ✅ 해당 날짜의 마지막 페이지 번호 가져오기
                    last_page = get_last_page(session, formatted_date)

                    # ✅ 2페이지부터 마지막 페이지까지 크롤링 (병렬 처리)
                    tasks += [executor.submit(fetch_news, session, formatted_date, page) for page in range(2, last_page + 1)]

                date_cursor += timedelta(days=1)

            # ✅ 병렬 요청 결과 처리
            for future in as_completed(tasks):
                result = future.result()
                if result:
                    news_titles.update(result)

    return list(news_titles)  # ✅ 최종 리스트 변환

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
    start_date = datetime(2025, 2, 1)
    end_date = datetime(2025, 2, 8)

    news_titles = get_news_titles_by_date(start_date, end_date)

    logging.info(f"\n📢 네이버 경제 뉴스 헤드라인 ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}):")
    print("\n".join(f"{i + 1}. {title}" for i, title in enumerate(news_titles[:10])))

    create_wordcloud(news_titles)