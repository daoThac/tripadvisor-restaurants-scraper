import os
import csv
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

HUE_REST_URL = "https://www.tripadvisor.com/Restaurants-g2146376-Thua_Thien_Hue_Province.html"
PROVINCE = "Thua Thien Hue"

def scrape():
    print("================== TRÌNH CÀO DỮ LIỆU NHÀ HÀNG TRIPADVISOR ==================")
    print("Khởi động tính năng Lưu Nối Tiếp. Đang đọc lại dữ liệu cũ nếu có...")
    
    # 1. Nạp danh sách nhà hàng đã cào
    existing_rests = set()
    rest_list = []
    if os.path.exists('restaurants_hue_summary.csv'):
        with open('restaurants_hue_summary.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_rests.add(row['restaurant_url'])
                rest_list.append(row)
        print(f"-> Đã tìm thấy {len(rest_list)} nhà hàng từ file cũ.")

    # 2. Nạp danh sách review đã cào (Duyệt theo ID: URL + Comment)
    existing_reviews = set()
    if os.path.exists('restaurants_hue_reviews_jan2025.csv'):
        with open('restaurants_hue_reviews_jan2025.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_reviews.add((row['url'], row['review']))
        print(f"-> Đã tìm thấy {len(existing_reviews)} reviews từ file cũ.")

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()
        
        # Lấy danh sách nhà hàng (Thay vì if len(rest_list) < 624, dỡ bỏ giới hạn)
        if True:
            print("\n=== BƯỚC 1: LẤY DANH SÁCH NHÀ HÀNG QUÁN CAFE LỚN ===")
            print("Đang truy cập danh sách nhà hàng tại Thừa Thiên Huế...")
            try:
                page.goto(HUE_REST_URL, timeout=60000)
                page.wait_for_timeout(5000)
                
                # Cố gắng click vào các bộ lọc nếu hiển thị (Restaurants, Coffee & Tea, Dessert, Bars & Pubs)
                # Thực tế việc truy cập URL tổng đã bao gồm đa phần các địa điểm này.
            except Exception as e:
                print(f"Lỗi khi tải trang ban đầu: {e}")
                
            page_num = 1
            
            file_exists = os.path.exists('restaurants_hue_summary.csv')
            with open('restaurants_hue_summary.csv', 'a', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['restaurant_url', 'restaurant_name', 'number_of_reviews'])
                if not file_exists:
                    writer.writeheader()
                # Chuyển vòng lặp lật trang thành vô hạn đến khi hết trang
                while True:
                    print(f"Đang duyệt trang danh sách thứ {page_num}...")
                    for _ in range(5):
                        page.mouse.wheel(0, 1000)
                        page.wait_for_timeout(1000)
                    
                    elements = page.locator('a[href*="/Restaurant_Review-"]').all()
                        
                    seen_this_page = set()
                    for el in elements:
                        try:
                            title = el.inner_text().strip()
                            href = el.get_attribute('href')
                            
                            # Thông thường tên quán ăn thường không trỗng và các element ảnh thường không có innerText rõ
                            if href and href not in seen_this_page and title and len(title) > 2:
                                seen_this_page.add(href)
                                title = re.sub(r'^\d+\.\s*', '', title)
                                rest_url = href if href.startswith("http") else "https://www.tripadvisor.com" + href
                                
                                # Lọc bỏ các links chứa #REVIEWS
                                if "#REVIEWS" in rest_url:
                                    continue

                                rest_data = {
                                    'restaurant_url': rest_url,
                                    'restaurant_name': title,
                                    'number_of_reviews': 'Xem khi lặp Review'
                                }
                                
                                if rest_url not in existing_rests:
                                    existing_rests.add(rest_url)
                                    rest_list.append(rest_data)
                                    writer.writerow(rest_data)
                                    f.flush()
                                    print(f"  + Lấy GIỮ MỚI: {title}")
                        except Exception:
                            pass
                            
                    next_btn = page.locator('a.nav.next.primary, a[aria-label="Next page"]')
                    if next_btn.count() > 0 and next_btn.is_visible():
                        try:
                            next_btn.click()
                            page.wait_for_timeout(4000)
                            page_num += 1
                        except Exception:
                            break
                    else:
                        print("Đã hết trang danh sách nhà hàng.")
                        break
        else:
            print("\n=== BƯỚC 1: HOÀN TẤT KIỂM TRA QUÉT DANH SÁCH ===")
        
        print(f"\n=== ĐÃ TÍCH LŨY TỔNG CỘNG {len(rest_list)} ĐỊA ĐIỂM ===")
        print("\n=== BƯỚC 2: CÀO REVIEWS TỪ T1/2025 ===")
        
        rev_file_exists = os.path.exists('restaurants_hue_reviews_jan2025.csv')
        with open('restaurants_hue_reviews_jan2025.csv', 'a', encoding='utf-8', newline='') as f2:
            fieldnames = ['url', 'user_id', 'title', 'review', 'rating', 'date_visited', 'trip_type', 'Year', 'Month', 'language', 'province']
            writer2 = csv.DictWriter(f2, fieldnames=fieldnames)
            if not rev_file_exists:
                writer2.writeheader()
                
            for idx, rest in enumerate(rest_list):
                print(f"\n[{idx+1}/{len(rest_list)}] Vào phân tích: {rest['restaurant_name']}")
                
                try:
                    page.goto(rest['restaurant_url'], timeout=60000)
                    page.wait_for_timeout(3000)
                    
                    lang_all_radio = page.locator('label[for*="language_filterLang_ALL"], input[value="ALL"][name="language"]')
                    if lang_all_radio.count() > 0:
                        try:
                            lang_all_radio.first.click(timeout=3000)
                            page.wait_for_timeout(2000)
                            print("  (Đã chuyển sang chế độ lấy mọi ngôn ngữ)")
                        except Exception:
                            pass
                    
                    review_page = 1
                    should_stop = False
                    total_reviews_saved_for_rest = 0
                    # Chuyển vòng lặp review thành vô hạn để lấy toàn bộ các review theo điều kiện
                    while True: 
                        page.wait_for_timeout(2000)
                        # Thêm selector hiện đại: data-automation="reviewCard"
                        review_cards = page.locator('div[data-automation="reviewCard"], div[data-test-target="HR_CC_CARD"]').all()
                        if not review_cards:
                            review_cards = page.locator('div[data-reviewid], .review-container').all()
                            
                        if not review_cards:
                            print("  Hết reviews trên trang này.")
                            break
                            
                        reviews_on_page = 0
                        skipped_reviews = 0
                        
                        for card in review_cards:
                            try:
                                data = card.evaluate('''node => {
                                    let title = "";
                                    let comment = "";
                                    let titleEl = node.querySelector('div[data-test-target="review-title"]');
                                    if (!titleEl) titleEl = node.querySelector('.noQuotes'); // Fallback old layout
                                    if (!titleEl) titleEl = node.querySelector('a[href*="/ShowUserReviews-"]');
                                    
                                    if (titleEl) {
                                        title = titleEl.innerText.trim();
                                    }
                                    
                                    let bodyEl = node.querySelector('[data-test-target="review-body"], div[data-automation="reviewText"], span[data-automation="reviewText"], .partial_entry');
                                    if (bodyEl) comment = bodyEl.innerText.replace(/Read more$/, '').replace(/Đọc thêm$/, '').trim();
                                    else {
                                        // Some new wrappers just put text loosely after the title
                                        if (titleEl && titleEl.nextElementSibling) {
                                            comment = titleEl.nextElementSibling.innerText.replace(/Read more$/, '').replace(/Đọc thêm$/, '').trim();
                                        }
                                    }
                                    
                                    let visit_date = "";
                                    let trip_type = "";
                                    
                                    // Parse date broad matching from node's full inner text
                                    let fullText = node.innerText || "";
                                    let writtenMatch = fullText.match(/(?:Written|Đã viết vào)\s+(?:on\s+)?([A-Za-z0-9\s,]+20\d{2})/i);
                                    if (writtenMatch) visit_date = writtenMatch[1].trim();
                                    else {
                                        let visitMatch = fullText.match(/(?:Date of visit|Date of experience|Ngày đi):\s*([A-Za-z0-9\s,]+20\d{2})/i);
                                        if (visitMatch) visit_date = visitMatch[1].trim();
                                        else {
                                            let maybeDate = fullText.match(/(?:[A-Z][a-z]{2}|thg|tháng)\s*\d*[\s,]*20\d{2}/i);
                                            if (maybeDate) visit_date = maybeDate[0].trim();
                                            else {
                                                let yearMatch = fullText.match(/20\d{2}/);
                                                if (yearMatch) visit_date = yearMatch[0];
                                            }
                                        }
                                    }
                                    
                                    let star = 0;
                                    let svg = node.querySelector('svg[data-automation="bubbleRatingImage"] title');
                                    if (svg) {
                                        let m = (svg.textContent || "").match(/([1-5])/);
                                        if (m) star = parseInt(m[1]);
                                    } else {
                                        let svg2 = node.querySelector('svg[aria-label*="bubbles"], .ui_bubble_rating');
                                        if (svg2) {
                                            let cls = svg2.getAttribute("class") || svg2.getAttribute("aria-label") || "";
                                            let m = cls.match(/bubble_(\d)0/);
                                            if (m) star = parseInt(m[1]);
                                            else {
                                                let m2 = cls.match(/([1-5])/);
                                                if (m2) star = parseInt(m2[1]);
                                            }
                                        }
                                    }
                                    
                                    let reviewer_url = "";
                                    let aProfile = node.querySelector('a[href*="/Profile/"]');
                                    if (!aProfile) aProfile = node.querySelector('.info_text > div > div'); // ID fallback
                                    if (aProfile) {
                                        reviewer_url = aProfile.innerText.trim() || ("https://www.tripadvisor.com" + aProfile.getAttribute("href"));
                                    }
                                    
                                    return {
                                        title: title,
                                        comment: comment,
                                        visit_date: visit_date,
                                        trip_type: trip_type,
                                        star: star,
                                        reviewer_url: reviewer_url
                                    };
                                }''')
                                
                                title = data.get('title', '')
                                comment = data.get('comment', '')
                                visit_date = data.get('visit_date', '')
                                trip_type = data.get('trip_type', '')
                                star = data.get('star', 0)
                                user_id = data.get('reviewer_url', '')
                                    
                                is_old = False
                                year = ""
                                month = ""
                                if visit_date:
                                    try:
                                        dt = datetime.strptime(visit_date, "%B %Y")
                                        year = str(dt.year)
                                        month = str(dt.month)
                                        if dt.year < 2025:
                                            should_stop = True
                                            is_old = True
                                    except:
                                        if "2024" in visit_date or "2023" in visit_date or "2022" in visit_date:
                                            should_stop = True
                                            is_old = True
                                        else:
                                            # Trích xuất số nếu có thể
                                            m = re.search(r'(20\d{2})', visit_date)
                                            if m:
                                                year = m.group(1)
                                                if int(year) < 2025:
                                                    should_stop = True
                                                    is_old = True
                                
                                if is_old: continue
                                
                                tupple_id = (rest['restaurant_url'], comment)
                                if tupple_id in existing_reviews:
                                    skipped_reviews += 1
                                    continue
                                
                                if comment:
                                    writer2.writerow({
                                        'url': rest['restaurant_url'],
                                        'user_id': user_id,
                                        'title': title,
                                        'review': comment,
                                        'rating': star,
                                        'date_visited': visit_date,
                                        'trip_type': trip_type,
                                        'Year': year,
                                        'Month': month,
                                        'language': 'all',
                                        'province': PROVINCE
                                    })
                                    f2.flush()
                                    existing_reviews.add(tupple_id)
                                    reviews_on_page += 1
                                    total_reviews_saved_for_rest += 1
                                    print(f"     + [Xong bài thứ {total_reviews_saved_for_rest}] => {title[:35]}...")
                                    
                            except Exception as e:
                                print(f"     [CẢNH BÁO] Bỏ qua 1 bài đánh giá do khác biệt cấu trúc HTML (Lỗi: {e})")
                        
                        if should_stop:
                            print(f"  ====> KẾT QUẢ: Chạm mốc tháng 1/2025. Tổng cộng cào được {total_reviews_saved_for_rest} bài của địa điểm này.")
                            break
                        
                        if reviews_on_page == 0 and skipped_reviews > 0:
                            print(f"  ====> BÁO CÁO: Toàn bộ trang {review_page} đều là review trùng cũ. Máy tiệp tục lật trang...")
                        
                        next_rv_btn = page.locator('a.ui_button.nav.next.primary, a[aria-label="Next page"]')
                        if next_rv_btn.count() > 0 and next_rv_btn.is_visible():
                            next_rv_btn.click()
                            review_page += 1
                        else:
                            print(f"  ====> KẾT QUẢ: Hết toàn bộ đánh giá. Tổng cộng cào được {total_reviews_saved_for_rest} bài của địa điểm này.")
                            break
                            
                except Exception as e:
                    print(f"Lỗi truy cập địa điểm {rest['restaurant_name']}: {e}")

        print("\nHOÀN THÀNH. Đã kết thúc việc cào dữ liệu và lưu nối tiếp 2 file CSV một cách an toàn.")
        browser.close()

if __name__ == '__main__':
    scrape()
