import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.jsoup.select.Elements;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

public class DartAlleyCrawler {
    
    // --- CONFIGURATION ---
    private static final int MAX_DEPTH = 2; // Depth of crawl
    private static final int MAX_LINKS_PER_PAGE = 10; // Grab 10 random new links per page

    private Set<String> visitedLinks = new HashSet<>();

    public void crawl(String url, int depth) {
        if (!visitedLinks.contains(url) && depth < MAX_DEPTH) {
            try {
                visitedLinks.add(url);
                
                // 1. CONNECT (Spoofing a real browser)
                Document document = Jsoup.connect(url)
                        .userAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                        .timeout(6000)
                        .ignoreHttpErrors(true)
                        .get();

                // 2. EXTRACT DATA
                String title = document.title().replace("\"", "'").replace("\\", "");
                String desc = "";
                
                // Try multiple ways to get a description
                Element metaDesc = document.selectFirst("meta[name=description]");
                if (metaDesc != null) {
                    desc = metaDesc.attr("content");
                } else {
                    Element firstP = document.selectFirst("p");
                    if(firstP != null) desc = firstP.text();
                }
                
                // Clean description
                desc = desc.replace("\"", "'").replace("\n", " ").replace("\r", " ");
                if (desc.length() > 250) desc = desc.substring(0, 250) + "...";
                if (desc.isEmpty()) desc = "No neural data available.";

                // 3. PRINT JSON OBJECT
                System.out.println("  {");
                System.out.println("    \"title\": \"" + title + "\",");
                System.out.println("    \"url\": \"" + url + "\",");
                System.out.println("    \"desc\": \"" + desc + "\"");
                System.out.println("  },");

                // 4. FIND NEW DOMAINS (Continuous Discovery)
                Elements links = document.select("a[href]");
                List<String> linksToVisit = new ArrayList<>();
                
                for (Element link : links) {
                    String nextUrl = link.attr("abs:href");
                    if (isValidLink(nextUrl)) {
                        linksToVisit.add(nextUrl);
                    }
                }

                // Shuffle to find random new corners of the web
                Collections.shuffle(linksToVisit);

                int count = 0;
                for (String nextUrl : linksToVisit) {
                    if (count >= MAX_LINKS_PER_PAGE) break;
                    crawl(nextUrl, depth + 1);
                    count++;
                }

            } catch (Exception e) {
                // Silent fail
            }
        }
    }

    private boolean isValidLink(String url) {
        if(url == null || url.length() < 10) return false;
        if(!url.startsWith("http")) return false;
        String lower = url.toLowerCase();
        return !lower.contains("login") && !lower.contains("signup");
    }

    public static void main(String[] args) {
        System.out.println("["); // Start JSON array
        
        // --- THE MASTER SEED LIST ---
        String[] seeds = {
            // 1. YOUR DOMAINS (Priority)
            "https://dartmeadow.com",
            "https://drymeadow.com",
            "https://radicaldeepscale.com",

            // 2. DISCOVERY HUBS (Aggregators that link to everywhere)
            "https://news.ycombinator.com",      // Hacker News
            "https://www.reddit.com/r/technology", // Reddit Tech
            "https://www.popurls.com",           // The "Mother of Aggregators"
            "https://techmeme.com",              // Tech Industry
            "https://github.com/trending",       // New Code

            // 3. GLOBAL AUTHORITIES
            "https://www.nasa.gov",
            "https://www.wired.com",
            "https://www.bbc.com/news"
        };

        DartAlleyCrawler bot = new DartAlleyCrawler();
        
        // Launch the fleet
        for (String seed : seeds) {
            try {
                bot.crawl(seed, 0);
            } catch (Exception e) { }
        }
        
        System.out.println("]"); // End JSON array
    }
}
