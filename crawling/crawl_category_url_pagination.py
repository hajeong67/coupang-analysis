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

def get_product_urls_from_category(driver, category_url, max_pages=5):
    urls = []

    for page in range(1, max_pages + 1):
        paged_url = f"{category_url}&page={page}"
        driver.get(paged_url)
        time.sleep(2)

        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "#productList li > a")))
            product_elements = driver.find_elements(By.CSS_SELECTOR, "#productList li > a")
        except:
            print(f"[경고] {page}페이지의 상품 목록이 로딩되지 않았습니다.")
            print(driver.page_source[:1000])
            break

        if not product_elements:
            print(f"❌ {page}페이지에 상품 없음 → 종료")
            break

        for elem in product_elements:
            href = elem.get_attribute("href")
            if href and "/vp/products/" in href:
                urls.append(href.split("?")[0])

        print(f"✅ {page}페이지 수집 완료 (누적: {len(urls)}개)")

    return urls

def crawl_product(driver, url, max_review_pages=80):
    print(f"\n상품 접근 중: {url}")
    driver.get(url)
    wait = WebDriverWait(driver, 10)

    try:
        product_name = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.prod-buy-header__title"))).text.strip()
    except:
        product_name = ""
        print("상품명 로딩 실패")

    try:
        seller = driver.find_element(By.CSS_SELECTOR, "div.prod-sale-vendor > a").text.strip()
    except:
        seller = "쿠팡"

    reviews = []

    try:
        review_tab = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "li.product-review")))
        driver.execute_script("arguments[0].click();", review_tab)
        print("✅ 리뷰 탭 클릭 성공")
        time.sleep(2)
    except:
        print("❌ 리뷰 탭 클릭 실패 또는 없음")
        return reviews

    current_page = 1
    while current_page <= max_review_pages:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article.sdp-review__article__list"))
            )
            review_elements = driver.find_elements(By.CSS_SELECTOR, "article.sdp-review__article__list")
        except:
            print("리뷰 로딩 실패 또는 없음")
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

        print(f"{current_page} 페이지 리뷰 수집 완료 (누적: {len(reviews)}개)")

        current_page += 1

        if current_page > max_review_pages:
            break

        try:
            page_buttons = driver.find_elements(By.CSS_SELECTOR, "button.sdp-review__article__page__num.js_reviewArticlePageBtn")
            button_clicked = False
            for btn in page_buttons:
                if btn.text.strip() == str(current_page):
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", btn)
                    print(f"➡️ 페이지 {current_page} 이동 완료")
                    button_clicked = True
                    time.sleep(2)
                    break

            if not button_clicked:
                next_button = driver.find_element(By.CSS_SELECTOR, "button.sdp-review__article__page__next")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", next_button)
                print(f"➡️ 다음 페이지 그룹으로 이동 완료 ({current_page} 페이지)")
                time.sleep(2)

        except Exception as e:
            print(f"페이지 이동 중 오류 발생 ({current_page} 페이지): {e}")
            break

    print(f"✅ 총 리뷰 수집 완료: {len(reviews)}개")
    return reviews


def main():
    category_url = "https://www.coupang.com/np/categories/564653?listSize=100"
    max_pages = 10
    max_review_pages = 80

    driver = get_driver()
    product_urls = get_product_urls_from_category(driver, category_url, max_pages=max_pages)

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

        if idx % 50 == 0:
            df = pd.DataFrame(all_data)
            df.insert(0, "INDEX", range(1, len(df) + 1))
            temp_filename = f"coupang_reviews_checkpoint_{idx}.csv"
            df.to_csv(temp_filename, index=False, encoding="utf-8-sig")
            print(f"⏸️ {idx}개 상품까지 저장 완료 → {temp_filename}")

    driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        df.insert(0, "INDEX", range(1, len(df) + 1))
        df.to_csv("coupang_fashion_reviews.csv", index=False, encoding="utf-8-sig")
        print(f"\n✅ 리뷰 저장 완료: coupang_fashion_reviews.csv (총 {len(df)}개 리뷰)")
    else:
        print("❌ 수집된 리뷰가 없습니다.")

if __name__ == "__main__":
    main()
