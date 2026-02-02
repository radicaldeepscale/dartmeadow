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
    // Depth 2 = The Seed -> Links on Seed -> Links on those pages.
    private static final int MAX_DEPTH = 2;
    // Limit how many links we follow per page to keep moving fast
    private static final int MAX_LINKS_PER_PAGE = 8; 

    private Set<String> visitedLinks = new HashSet<>();

    public void crawl(String url, int depth) {
        if (!visitedLinks.contains(url) && depth < MAX_DEPTH) {
            try {
                visitedLinks.add(url);
                
                // 1. CONNECT (Spoofing a real browser to avoid blocks)
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
                    // Fallback: First paragraph of text
                    Element firstP = document.selectFirst("p");
                    if(firstP != null) desc = firstP.text();
                }
                
                // Clean the description for JSON
                desc = desc.replace("\"", "'").replace("\n", " ").replace("\r", " ");
                if (desc.length() > 200) desc = desc.substring(0, 200) + "...";
                if (desc.isEmpty()) desc = "No neural data available.";

                // 3. PRINT JSON OBJECT
                System.out.println("  {");
                System.out.println("    \"title\": \"" + title + "\",");
                System.out.println("    \"url\": \"" + url + "\",");
                System.out.println("    \"desc\": \"" + desc + "\"");
                System.out.println("  },");

                // 4. FIND NEW DOMAINS (The "Continuous Discovery" Logic)
                Elements links = document.select("a[href]");
                List<String> linksToVisit = new ArrayList<>();
                
                for (Element link : links) {
                    String nextUrl = link.attr("abs:href");
                    
                    // Filter out garbage links
                    if (isValidLink(nextUrl)) {
                        linksToVisit.add(nextUrl);
                    }
                }

                // RANDOMIZE: Shuffle links so we don't just follow the menu bar
                Collections.shuffle(linksToVisit);

                // EXPLORE: Follow a few random links
                int count = 0;
                for (String nextUrl : linksToVisit) {
                    if (count >= MAX_LINKS_PER_PAGE) break;
                    crawl(nextUrl, depth + 1);
                    count++;
                }

            } catch (Exception e) {
                // Silent fail to keep output clean
            }
        }
    }

    // Helper to skip boring links like "login" or "privacy policy"
    private boolean isValidLink(String url) {
        if(url == null || url.length() < 10) return false;
        if(!url.startsWith("http")) return false;
        
        String lower = url.toLowerCase();
        return !lower.contains("login") && 
               !lower.contains("signup") && 
               !lower.contains("facebook.com") && // Skip social traps
               !lower.contains("twitter.com") &&
               !lower.contains("linkedin.com");
    }

    public static void main(String[] args) {
        System.out.println("["); // Start JSON array
        
        // --- THE MASTER SEED LIST ---
        // These sites link to THOUSANDS of other new domains daily.
        String[] seeds = {
            // AGGREGATORS (The "Hubs" of the web)
            "https://news.ycombinator.com",      // Hacker News (Tech)
            "https://www.reddit.com/r/technology", // Reddit Tech
            "https://www.drudgereport.com",      // Global News Links
            "https://techmeme.com",              // Tech Industry
            "https://www.popurls.com",           // The "Mother of Aggregators"

            // DISCOVERY ENGINES
            "https://github.com/trending",       // New Code Projects
            "https://medium.com/topic/technology", // New Articles
            "https://www.producthunt.com",       // New Startups
            
            // MAJOR AUTHORITIES
            "https://www.nasa.gov",
            "https://www.bbc.com/news",
            "https://www.wired.com",
            "https://radicaldeepscale.com"       // Your Domain
        };

        DartAlleyCrawler bot = new DartAlleyCrawler();
        
        // Launch the fleet
        for (String seed : seeds) {
            try {
                // Thread.sleep(1000); // Optional polite pause between seeds
                bot.crawl(seed, 0);
            } catch (Exception e) {
                // Ignore bad seed
            }
        }
        
        System.out.println("]"); // End JSON array
    }
}                System.out.println("  {");
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
