import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import java.io.IOException;
import java.util.HashSet;
import java.util.Set;

public class DartAlleyCrawler {
    // SETTINGS: Change the MAX_DEPTH to crawl deeper (1 = just the first page)
    private static final int MAX_DEPTH = 1;
    private Set<String> visitedLinks = new HashSet<>();

    public void crawl(String url, int depth) {
        if ((!visitedLinks.contains(url) && (depth < MAX_DEPTH))) {
            try {
                visitedLinks.add(url);
                // Connect to the web page
                Document document = Jsoup.connect(url)
                        .userAgent("DART-Alley-Bot/1.0")
                        .timeout(5000)
                        .get();

                // Extract Data
                String title = document.title().replace("\"", "'");
                String desc = "";
                
                // Try to find the meta description
                Element metaDesc = document.selectFirst("meta[name=description]");
                if (metaDesc != null) {
                    desc = metaDesc.attr("content").replace("\"", "'");
                } else {
                    desc = "No description available for this neural node.";
                }

                // PRINT VALID JSON FORMAT
                System.out.println("  {");
                System.out.println("    \"title\": \"" + title + "\",");
                System.out.println("    \"url\": \"" + url + "\",");
                System.out.println("    \"desc\": \"" + desc + "\"");
                System.out.println("  },");

                // Find more links to crawl
                Elements linksOnPage = document.select("a[href]");
                depth++;
                for (Element page : linksOnPage) {
                    // Recursive crawl
                    crawl(page.attr("abs:href"), depth);
                }

            } catch (IOException e) {
                // Ignore broken links to keep output clean
            }
        }
    }

    public static void main(String[] args) {
        System.out.println("[\n  // COPY THESE RESULTS INTO YOUR database.json");
        
        // === CHANGE THIS URL TO START CRAWLING A NEW SITE ===
        new DartAlleyCrawler().crawl("https://en.wikipedia.org/wiki/Artificial_intelligence", 0);
        
        System.out.println("]");
    }
}
