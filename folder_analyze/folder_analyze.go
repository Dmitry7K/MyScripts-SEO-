package main

import (
	"bufio"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

type LinkStatus struct {
	IsWorking  bool
	StatusCode int
}

func main() {
	rootDir := "/Users/dmitrijkovalev/folder_analyze/baza" // Измените на путь к вашей корневой папке
	results := make(map[string]LinkStatus)
	var mutex sync.Mutex
	var wg sync.WaitGroup

	var processedFiles, processedLinks, workingLinks atomic.Int64
	startTime := time.Now()

	go func() {
		for {
			time.Sleep(5 * time.Second)
			files := processedFiles.Load()
			links := processedLinks.Load()
			working := workingLinks.Load()
			elapsed := time.Since(startTime).Round(time.Second)
			fmt.Printf("Прогресс: обработано файлов: %d, ссылок: %d (работающих: %d) за %s\n",
				files, links, working, elapsed)
		}
	}()

	err := filepath.Walk(rootDir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && strings.HasSuffix(info.Name(), ".txt") {
			wg.Add(1)
			go func(filePath string) {
				defer wg.Done()
				processFile(filePath, &results, &mutex, &processedLinks, &workingLinks)
				processedFiles.Add(1)
			}(path)
		}
		return nil
	})
	if err != nil {
		fmt.Printf("Ошибка при обходе директорий: %v\n", err)
		return
	}

	wg.Wait()

	// Вывод итоговой статистики
	totalFiles := processedFiles.Load()
	totalLinks := processedLinks.Load()
	totalWorking := workingLinks.Load()
	totalTime := time.Since(startTime).Round(time.Second)
	fmt.Printf("\nИтого:\n")
	fmt.Printf("Обработано файлов: %d\n", totalFiles)
	fmt.Printf("Проверено ссылок: %d\n", totalLinks)
	fmt.Printf("Работающих ссылок: %d (%.2f%%)\n", totalWorking, float64(totalWorking)/float64(totalLinks)*100)
	fmt.Printf("Общее время выполнения: %s\n", totalTime)

	// Сохранение результатов
	saveResults(results)
}

func processFile(filePath string, results *map[string]LinkStatus, mutex *sync.Mutex, processedLinks, workingLinks *atomic.Int64) {
	file, err := os.Open(filePath)
	if err != nil {
		fmt.Printf("Ошибка при открытии файла %s: %v\n", filePath, err)
		return
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		link := strings.TrimSpace(scanner.Text())
		if link != "" {
			processedLinks.Add(1)
			isWorking, statusCode := checkLink(link)
			if isWorking {
				workingLinks.Add(1)
			}
			mutex.Lock()
			(*results)[link] = LinkStatus{IsWorking: isWorking, StatusCode: statusCode}
			mutex.Unlock()
		}
	}
}

func checkLink(link string) (bool, int) {
	if !strings.HasPrefix(link, "http://") && !strings.HasPrefix(link, "https://") {
		link = "http://" + link
	}

	client := &http.Client{
		Timeout: 10 * time.Second,
		Transport: &http.Transport{
			DisableKeepAlives: true,
		},
	}

	req, err := http.NewRequest("GET", link, nil)
	if err != nil {
		fmt.Printf("Ошибка при создании запроса для %s: %v\n", link, err)
		return false, 0
	}

	req.Close = true

	resp, err := client.Do(req)
	if err != nil {
		if strings.Contains(err.Error(), "protocol error") || strings.Contains(err.Error(), "Unsolicited response") {
			// Просто игнорируем эти ошибки, так как они не означают, что ссылка не работает
			return false, 0
		} else {
			fmt.Printf("Ошибка при проверке %s: %v\n", link, err)
			return false, 0
		}
	}
	defer resp.Body.Close()

	_, err = io.Copy(io.Discard, resp.Body)
	if err != nil {
		fmt.Printf("Ошибка при чтении тела ответа для %s: %v\n", link, err)
		return false, resp.StatusCode
	}

	return resp.StatusCode == http.StatusOK, resp.StatusCode
}

func saveResults(results map[string]LinkStatus) {
	file, err := os.Create("backlinks_results.txt")
	if err != nil {
		fmt.Printf("Error creating results file: %v\n", err)
		return
	}
	defer file.Close()

	// Write working links first
	_, err = file.WriteString("Working links:\n")
	if err != nil {
		fmt.Printf("Error writing header: %v\n", err)
	}
	for link, status := range results {
		if status.IsWorking {
			_, err := file.WriteString(fmt.Sprintf("%s - working\n", link))
			if err != nil {
				fmt.Printf("Error writing result: %v\n", err)
			}
		}
	}

	// Write not working links
	_, err = file.WriteString("\nNot working links:\n")
	if err != nil {
		fmt.Printf("Error writing header: %v\n", err)
	}
	for link, status := range results {
		if !status.IsWorking {
			_, err := file.WriteString(fmt.Sprintf("%s - not working\n", link))
			if err != nil {
				fmt.Printf("Error writing result: %v\n", err)
			}
		}
	}
}
