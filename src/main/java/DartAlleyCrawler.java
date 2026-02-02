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
    private static final int MAX_LINKS_PER_PAGE = 10;
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
                    .userAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    .timeout(10000)
                    .followRedirects(true)
                    .get();

            String title = document.title().trim();
            if (title.isEmpty()) title = "Neural Node: " + url;

            String desc = document.select("meta[name=description]").attr("content").trim();
            if (desc.isEmpty()) {
                desc = document.select("meta[property=og:description]").attr("content").trim();
            }
            if (desc.isEmpty()) {
                // Try to find the first significant paragraph
                for (Element p : document.select("p")) {
                    String pText = p.text().trim();
                    if (pText.length() > 20) {
                        desc = pText;
                        break;
                    }
                }
            }

            if (desc.length() > 200) {
                desc = desc.substring(0, 197) + "...";
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

        if (args.length > 0) {
            for (String seed : args) {
                crawler.crawl(seed, 0);
            }
        } else {
            // Default diverse seeds to ensure "world wide web" reach
            String[] defaultSeeds = {
                "https://www.nasa.gov",
                "https://www.spacex.com",
                "https://en.wikipedia.org/wiki/Aerospace_engineering",
                "https://www.lockheedmartin.com",
                "https://www.boeing.com"
            };
            for (String seed : defaultSeeds) {
                crawler.crawl(seed, 0);
            }
        }

        crawler.saveResults("database.json");
    }
}
