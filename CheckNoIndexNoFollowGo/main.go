package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/tebeka/selenium"
	"github.com/tebeka/selenium/chrome"
)

func checkNoIndexNoFollow(url string, useSelenium bool) (bool, error) {
	var html string
	var err error

	if useSelenium {
		html, err = getHTMLWithSelenium(url)
	} else {
		html, err = getHTMLWithHTTP(url)
	}
	if err != nil {
		return false, err
	}

	return checkRobotsMetaTag(html), nil
}

func getHTMLWithSelenium(url string) (string, error) {
	const (
		seleniumPath     = "vendor/selenium-server-standalone.jar"
		chromeDriverPath = "chromedriver"
		port             = 8080
	)
	opts := []selenium.ServiceOption{
		selenium.StartFrameBuffer(),
		selenium.ChromeDriver(chromeDriverPath),
	}
	selenium.SetDebug(true)
	service, err := selenium.NewSeleniumService(seleniumPath, port, opts...)
	if err != nil {
		return "", fmt.Errorf("error starting the Selenium server: %v", err)
	}
	defer service.Stop()

	caps := selenium.Capabilities{"browserName": "chrome"}
	chromeCaps := chrome.Capabilities{
		Args: []string{"--headless"},
	}
	caps.AddChrome(chromeCaps)

	wd, err := selenium.NewRemote(caps, fmt.Sprintf("http://localhost:%d/wd/hub", port))
	if err != nil {
		return "", fmt.Errorf("failed to open session: %v", err)
	}
	defer wd.Quit()

	if err = wd.Get(url); err != nil {
		return "", fmt.Errorf("failed to load page: %v", err)
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	var html string
	for {
		select {
		case <-ctx.Done():
			return "", fmt.Errorf("timeout waiting for page source")
		default:
			html, err = wd.PageSource()
			if err == nil {
				return html, nil
			}
			time.Sleep(100 * time.Millisecond)
		}
	}
}

func getHTMLWithHTTP(url string) (string, error) {
	resp, err := http.Get(url)
	if err != nil {
		return "", fmt.Errorf("failed to fetch page: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read page body: %v", err)
	}
	return string(body), nil
}

func checkRobotsMetaTag(html string) bool {
	robotsPatterns := []string{
		`name="robots" content="noindex"`,
		`name="robots" content="nofollow"`,
		`name="robots" content="none"`,
		`name="robots" content="noindex, nofollow"`,
		`name="robots" content="nofollow, noindex"`,
	}

	for _, pattern := range robotsPatterns {
		if strings.Contains(html, pattern) {
			return true
		}
	}
	return false
}

func main() {
	url := "https://example.com"
	useSelenium := true // Можно изменить на false для использования HTTP

	result, err := checkNoIndexNoFollow(url, useSelenium)
	if err != nil {
		fmt.Println("Ошибка:", err)
		os.Exit(1)
	}

	if result {
		fmt.Printf("Внимание! Сайт %s содержит теги noindex или nofollow.\n", url)
	} else {
		fmt.Printf("Сайт %s открыт для индексации.\n", url)
	}
}
