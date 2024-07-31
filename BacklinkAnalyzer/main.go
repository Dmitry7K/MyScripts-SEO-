package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/temoto/robotstxt"
	"golang.org/x/net/html"
)

type Backlink struct {
	SourceURL  string `json:"source_url"`
	AnchorText string `json:"anchor_text"`
}

type Config struct {
	TargetURL    string
	MaxDepth     int
	MaxWorkers   int
	OutputFile   string
	IgnoreRobots bool
}

var (
	visited     = make(map[string]bool)
	visitedLock sync.Mutex
	semaphore   chan struct{}
)

func main() {
	// Флаги командной строки для CLI использования
	targetURL := flag.String("url", "", "URL для анализа")
	maxDepth := flag.Int("depth", 2, "Максимальная глубина обхода")
	maxWorkers := flag.Int("workers", 10, "Максимальное количество одновременных запросов")
	outputFile := flag.String("output", "", "Файл для сохранения результатов")
	ignoreRobots := flag.Bool("ignore-robots", false, "Игнорировать robots.txt")
	serverMode := flag.Bool("server", false, "Запустить в режиме веб-сервера")

	flag.Parse()

	if *serverMode {
		runServer()
	} else {
		runCLI(*targetURL, *maxDepth, *maxWorkers, *outputFile, *ignoreRobots)
	}
}

func runServer() {
	http.HandleFunc("/", serveHTML)
	http.HandleFunc("/analyze", handleAnalyze)

	fmt.Println("Сервер запущен на http://localhost:8080")
	http.ListenAndServe(":8080", nil)
}

func serveHTML(w http.ResponseWriter, r *http.Request) {
	http.ServeFile(w, r, "index.html")
}

func handleAnalyze(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Метод не разрешен", http.StatusMethodNotAllowed)
		return
	}

	url := r.FormValue("url")
	if url == "" {
		http.Error(w, "URL не указан", http.StatusBadRequest)
		return
	}

	config := Config{
		TargetURL:    url,
		MaxDepth:     2,
		MaxWorkers:   10,
		IgnoreRobots: false,
	}

	var backlinks []Backlink
	var err error

	done := make(chan bool)
	go func() {
		defer func() {
			if r := recover(); r != nil {
				err = fmt.Errorf("Произошла ошибка при анализе: %v", r)
			}
			done <- true
		}()
		backlinks = getBacklinks(config)
	}()

	select {
	case <-done:
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		if err := json.NewEncoder(w).Encode(backlinks); err != nil {
			http.Error(w, "Ошибка при кодировании результатов", http.StatusInternalServerError)
			return
		}
	case <-time.After(30 * time.Second):
		http.Error(w, "Время ожидания истекло", http.StatusRequestTimeout)
	}
}

func runCLI(targetURL string, maxDepth, maxWorkers int, outputFile string, ignoreRobots bool) {
	if targetURL == "" {
		fmt.Println("Необходимо указать URL для анализа")
		os.Exit(1)
	}

	config := Config{
		TargetURL:    targetURL,
		MaxDepth:     maxDepth,
		MaxWorkers:   maxWorkers,
		OutputFile:   outputFile,
		IgnoreRobots: ignoreRobots,
	}

	backlinks := getBacklinks(config)

	fmt.Printf("Найдено %d обратных ссылок для %s\n", len(backlinks), config.TargetURL)
	for _, link := range backlinks {
		fmt.Printf("Источник: %s, Анкор: %s\n", link.SourceURL, link.AnchorText)
	}

	if config.OutputFile != "" {
		saveToFile(backlinks, config.OutputFile)
	}
}

func getBacklinks(config Config) []Backlink {
	var backlinks []Backlink
	var wg sync.WaitGroup
	var mu sync.Mutex

	semaphore = make(chan struct{}, config.MaxWorkers)

	crawl(config.TargetURL, config, 0, &wg, &mu, &backlinks)

	wg.Wait()
	return backlinks
}

func crawl(pageURL string, config Config, depth int, wg *sync.WaitGroup, mu *sync.Mutex, backlinks *[]Backlink) {
	if depth > config.MaxDepth {
		return
	}

	visitedLock.Lock()
	if visited[pageURL] {
		visitedLock.Unlock()
		return
	}
	visited[pageURL] = true
	visitedLock.Unlock()

	semaphore <- struct{}{}
	wg.Add(1)

	go func() {
		defer wg.Done()
		defer func() { <-semaphore }()
		defer func() {
			if r := recover(); r != nil {
				fmt.Printf("Восстановление после паники при обработке %s: %v\n", pageURL, r)
			}
		}()

		if !config.IgnoreRobots {
			allowed, err := isAllowedByRobots(pageURL)
			if err != nil || !allowed {
				fmt.Printf("Доступ запрещен robots.txt или произошла ошибка для %s: %v\n", pageURL, err)
				return
			}
		}

		links, err := findBacklinksOnPage(pageURL, config.TargetURL)
		if err != nil {
			fmt.Printf("Ошибка при обработке %s: %v\n", pageURL, err)
			return
		}

		mu.Lock()
		*backlinks = append(*backlinks, links...)
		mu.Unlock()

		fmt.Printf("Найдено %d ссылок на %s\n", len(links), pageURL)

		doc, err := fetchAndParse(pageURL)
		if err != nil {
			fmt.Printf("Ошибка при получении и парсинге %s: %v\n", pageURL, err)
			return
		}

		var pageLinks []string
		var f func(*html.Node)
		f = func(n *html.Node) {
			if n == nil {
				return
			}
			if n.Type == html.ElementNode && n.Data == "a" {
				for _, a := range n.Attr {
					if a.Key == "href" {
						link, err := url.Parse(a.Val)
						if err != nil {
							fmt.Printf("Ошибка при парсинге URL %s: %v\n", a.Val, err)
							continue
						}
						sourceURLParsed, err := url.Parse(pageURL)
						if err != nil {
							fmt.Printf("Ошибка при парсинге источника URL %s: %v\n", pageURL, err)
							continue
						}
						if link == nil || sourceURLParsed == nil {
							continue
						}
						absolute := sourceURLParsed.ResolveReference(link)
						if absolute == nil {
							continue
						}
						if absolute.Host != "" && absolute.Host != sourceURLParsed.Host {
							pageLinks = append(pageLinks, absolute.String())
						}
					}
				}
			}
			for c := n.FirstChild; c != nil; c = c.NextSibling {
				f(c)
			}
		}
		f(doc)

		for _, link := range pageLinks {
			crawl(link, config, depth+1, wg, mu, backlinks)
		}
	}()
}

func isAllowedByRobots(pageURL string) (bool, error) {
	parsedURL := parseURL(pageURL)
	robotsURL := fmt.Sprintf("%s://%s/robots.txt", parsedURL.Scheme, parsedURL.Host)

	resp, err := http.Get(robotsURL)
	if err != nil {
		return false, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return true, nil
	}

	robots, err := robotstxt.FromResponse(resp)
	if err != nil {
		return false, err
	}

	return robots.TestAgent(parsedURL.Path, "BacklinkAnalyzer"), nil
}

func findBacklinksOnPage(sourceURL, targetURL string) ([]Backlink, error) {
	doc, err := fetchAndParse(sourceURL)
	if err != nil {
		return nil, err
	}

	var backlinks []Backlink
	var f func(*html.Node)
	f = func(n *html.Node) {
		if n == nil {
			return
		}
		if n.Type == html.ElementNode && n.Data == "a" {
			for _, a := range n.Attr {
				if a.Key == "href" {
					link, err := url.Parse(a.Val)
					if err != nil {
						fmt.Printf("Ошибка при парсинге URL %s: %v\n", a.Val, err)
						continue
					}
					sourceURLParsed, err := url.Parse(sourceURL)
					if err != nil {
						fmt.Printf("Ошибка при парсинге источника URL %s: %v\n", sourceURL, err)
						continue
					}
					if link == nil || sourceURLParsed == nil {
						continue
					}
					absolute := sourceURLParsed.ResolveReference(link)
					if absolute == nil {
						continue
					}
					if strings.Contains(absolute.String(), targetURL) {
						backlinks = append(backlinks, Backlink{
							SourceURL:  sourceURL,
							AnchorText: getAnchorText(n),
						})
					}
					break
				}
			}
		}
		for c := n.FirstChild; c != nil; c = c.NextSibling {
			f(c)
		}
	}
	f(doc)

	return backlinks, nil
}

func fetchAndParse(url string) (*html.Node, error) {
	resp, err := http.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("получен статус %d", resp.StatusCode)
	}

	doc, err := html.Parse(resp.Body)
	if err != nil {
		return nil, err
	}

	return doc, nil
}

func getAnchorText(n *html.Node) string {
	var text string
	for c := n.FirstChild; c != nil; c = c.NextSibling {
		if c.Type == html.TextNode {
			text += c.Data
		}
	}
	return strings.TrimSpace(text)
}

func parseURL(rawURL string) *url.URL {
	u, err := url.Parse(rawURL)
	if err != nil {
		panic(err)
	}
	return u
}

func saveToFile(backlinks []Backlink, filename string) {
	file, err := os.Create(filename)
	if err != nil {
		fmt.Printf("Ошибка при создании файла: %v\n", err)
		return
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(backlinks); err != nil {
		fmt.Printf("Ошибка при сохранении в файл: %v\n", err)
	}
}
