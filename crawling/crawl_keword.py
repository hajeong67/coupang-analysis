import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import numpy as np
import time
import re

def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")
    return uc.Chrome(options=options, headless=False)

# 쿠팡 검색 결과에서 상품 링크 수집
def get_product_urls_from_search(driver, keyword, max_products=10):
    search_url = f"https://www.coupang.com/np/search?q={keyword}"
    driver.get(search_url)
    time.sleep(3)

    urls = []
    elements = driver.find_elements(By.CSS_SELECTOR, "a.search-product-link")

    for e in elements[:max_products]:
        href = e.get_attribute("href")
        if href and "coupang.com" in href:
            urls.append(href if href.startswith("http") else "https://www.coupang.com" + href)

    print(f"총 {len(urls)}개 상품 URL 수집됨")
    return urls

# 판매자 정보 추출
def extract_seller(driver):
    try:
        return driver.find_element(By.CSS_SELECTOR, "div.prod-sale-vendor > a").text.strip()
    except:
        pass
    try:
        rows = driver.find_elements(By.CSS_SELECTOR, "table.prod-delivery-return-policy tr")
        for row in rows:
            try:
                th = row.find_element(By.TAG_NAME, "th").text.strip()
                if "판매자" in th or "화장품책임판매업자" in th:
                    return row.find_element(By.TAG_NAME, "td").text.strip()
            except:
                continue
    except:
        pass
    return "쿠팡"

# 리뷰 수집
def crawl_product(driver, url, max_review_pages=40):
    print(f"\n상품 접근 중: {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    try:
        product_name = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.prod-buy-header__title"))).text.strip()
    except:
        product_name = ""
        print("상품명 로딩 실패")

    seller = extract_seller(driver)
    print(f"판매자: {seller}")

    reviews = []

    # 리뷰 탭 진입: 점진 스크롤 + 전체 스크롤 백업
    found_review_tab = False
    for percent in range(10, 100, 10):
        driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {percent / 100});")
        time.sleep(1.2)
        try:
            review_tab = driver.find_element(By.CSS_SELECTOR, 'a.sdp-review__article__headline__overview__total')
            review_tab.click()
            print(f"리뷰 탭 클릭 성공 (스크롤 {percent}%)")
            time.sleep(2)
            found_review_tab = True
            break
        except:
            continue

    if not found_review_tab:
        print("리뷰 탭 발견 실패 → 페이지 끝까지 스크롤")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

    # 리뷰 페이지 순회
    current_page = 1

    while current_page <= max_review_pages:
        try:
            review_elements = wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.sdp-review__article__list"))
            )
        except:
            print("리뷰 로딩 실패 또는 없음")
            break

        if not review_elements:
            print("리뷰 요소 없음 → 종료")
            break

        for r in review_elements:
            try:
                star_style = r.find_element(By.CSS_SELECTOR, "div.sdp-review__article__list__info__product-info__star-gray > div").get_attribute("style")
                width_match = re.search(r'width:\s*(\d+)%', star_style)
                rating = str(round(float(width_match.group(1)) / 20, 1)) if width_match else ""
            except:
                rating = ""
            try:
                title = r.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__headline').text.strip()
            except:
                title = ""
            try:
                content = r.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__review__content').text.strip()
            except:
                content = ""
            try:
                helpful = r.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__help__count').text.strip().replace("도움돼요", "").strip()
            except:
                helpful = "0"
            try:
                date = r.find_element(By.CSS_SELECTOR, 'div.sdp-review__article__list__info__product-info__reg-date').text.strip()
            except:
                date = ""

            reviews.append({
                "URL": url,
                "상품명": product_name,
                "판매자": seller,
                "구매자 평점": rating,
                "리뷰 제목": title,
                "리뷰 내용": content,
                "리뷰로부터 도움받은 수": helpful,
                "날짜": date
            })

        current_page += 1
        try:
            # 버튼 강제 렌더링: 아래로 스크롤
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            page_buttons = driver.find_elements(By.CSS_SELECTOR, "button.sdp-review__article__page__num.js_reviewArticlePageBtn")

            found = False
            for btn in page_buttons:
                if btn.text.strip() == str(current_page):
                    driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"{current_page} 페이지 이동 완료")
                    time.sleep(2)
                    found = True
                    break

            if not found:
                print(f"{current_page} 페이지 버튼 없음 → 종료")
                break

        except Exception as e:
            print(f"{current_page} 페이지 버튼 클릭 실패: {e}")
            break

    print(f"총 리뷰 수집 완료: {len(reviews)}개")
    return reviews

def main():
    keyword = "사과"
    max_products = 120              # 수집할 상품 수
    max_review_pages = 200         # 상품당 최대 리뷰 페이지 수

    driver = get_driver()
    product_urls = get_product_urls_from_search(driver, keyword, max_products=max_products)

    print(f"\n총 {len(product_urls)}개의 상품에서 리뷰를 수집합니다.\n")
    all_data = []

    for idx, url in enumerate(product_urls, 1):
        try:
            print(f"\n[{idx}/{len(product_urls)}] 상품 크롤링 시작")
            reviews = crawl_product(driver, url, max_review_pages=max_review_pages)
            all_data.extend(reviews)
        except Exception as e:
            print(f"오류 발생: {e}")
        time.sleep(2)

    driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        df.insert(0, "INDEX", range(1, len(df) + 1))
        df.to_csv(f"{keyword}_reviews.csv", index=False, encoding="utf-8-sig")
        print(f"\n 리뷰 저장 완료: {keyword}_reviews.csv (총 {len(df)}개 리뷰)")
    else:
        print("수집된 리뷰가 없습니다.")


if __name__ == "__main__":
    main()