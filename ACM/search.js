document.addEventListener("DOMContentLoaded", async () => {
    const resultsContainer = document.getElementById("results-container");
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');

    if (query) {
        resultsContainer.innerHTML = '<p>Loading...</p>';

        try {
            const response = await fetch("http://127.0.0.1:8000/search", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ text: query }),
            });

            if (!response.ok) {
                throw new Error("Network response was not ok");
            }

            const data = await response.json();
            resultsContainer.innerHTML = `<div class="prose dark:prose-invert max-w-none">${data.reply}</div>`;
        } catch (error) {
            resultsContainer.innerHTML = '<p>An error occurred while fetching the search results.</p>';
            console.error("Error:", error);
        }
    } else {
        resultsContainer.innerHTML = '<p>Please ask a question from the AI Chat page.</p>';
    }
});