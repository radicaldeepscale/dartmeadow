import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;

import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DartAlleyCrawler {
    private static final int MAX_DEPTH = 2;
    private static final int MAX_LINKS_PER_PAGE = 5; // Limit links to avoid timeout
    private Set<String> visitedLinks = new HashSet<>();
    private List<PageData> results = new ArrayList<>();

    static class PageData {
        String title;
        String url;
        String desc;

        PageData(String title, String url, String desc) {
            this.title = title;
            this.url = url;
            this.desc = desc;
        }
    }

    public void crawl(String url, int depth) {
        if (depth >= MAX_DEPTH || visitedLinks.contains(url)) {
            return;
        }

        try {
            visitedLinks.add(url);
            System.out.println("Crawling: " + url + " (depth: " + depth + ")");

            Document document = Jsoup.connect(url)
                    .userAgent("DART-Alley-Crawler/1.0 (+https://dartmeadow.com)")
                    .timeout(5000)
                    .get();

            String title = document.title().trim();
            if (title.isEmpty()) title = "Untitled Node";

            String desc = document.select("meta[name=description]").attr("content").trim();
            if (desc.isEmpty()) {
                desc = document.select("meta[property=og:description]").attr("content").trim();
            }
            if (desc.isEmpty()) {
                Element firstP = document.select("p").first();
                if (firstP != null) {
                    desc = firstP.text();
                    if (desc.length() > 150) {
                        desc = desc.substring(0, 147) + "...";
                    }
                }
            }
            if (desc.isEmpty()) {
                desc = "No description available for this neural pathway.";
            }

            results.add(new PageData(title, url, desc));

            if (depth < MAX_DEPTH - 1) {
                Elements linksOnPage = document.select("a[href]");
                int count = 0;
                for (Element page : linksOnPage) {
                    if (count >= MAX_LINKS_PER_PAGE) break;
                    String absUrl = page.attr("abs:href");
                    // Simple check to keep it relevant and avoid huge sites
                    if (absUrl.startsWith("http") && !visitedLinks.contains(absUrl) && !absUrl.contains("#")) {
                        crawl(absUrl, depth + 1);
                        count++;
                    }
                }
            }
        } catch (IOException e) {
            System.err.println("Error crawling " + url + ": " + e.getMessage());
        }
    }

    public void saveResults(String filename) {
        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        try (FileWriter writer = new FileWriter(filename)) {
            gson.toJson(results, writer);
            System.out.println("Saved " + results.size() + " results to " + filename);
        } catch (IOException e) {
            System.err.println("Error saving results: " + e.getMessage());
        }
    }

    public static void main(String[] args) {
        DartAlleyCrawler crawler = new DartAlleyCrawler();
        crawler.crawl("https://en.wikipedia.org/wiki/Artificial_intelligence", 0);
        crawler.saveResults("database.json");
    }
}
