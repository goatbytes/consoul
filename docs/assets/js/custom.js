/**
 * Custom JavaScript for Consoul Documentation
 * Initializes Termynal animated terminals
 */

function setupTermynal() {
    document.querySelectorAll(".use-termynal").forEach(node => {
        node.style.display = "block";
        new Termynal(node, {
            lineDelay: 500
        });
    });
    const progressLiteralStart = "---> 100%";
    const promptLiteralStart = "$ ";
    const customPromptLiteralStart = "# ";
    const termynalActivateClass = "termy";
    let termynals = [];

    function createTermynals() {
        document
            .querySelectorAll(`.${termynalActivateClass} .highlight code`)
            .forEach(node => {
                const text = node.textContent;
                const lines = text.split("\n");
                const useLines = [];
                let buffer = [];
                function saveBuffer() {
                    if (buffer.length) {
                        let isBlankSpace = true;
                        buffer.forEach(line => {
                            if (line) {
                                isBlankSpace = false;
                            }
                        });
                        dataValue = {};
                        if (isBlankSpace) {
                            dataValue["delay"] = 0;
                        }
                        if (buffer[buffer.length - 1] === "") {
                            // A last single <br> won't have effect
                            // so put an additional one
                            buffer.push("");
                        }
                        const bufferDiv = document.createElement("div");
                        bufferDiv.innerHTML = buffer.join("<br>");
                        dataValue["value"] = bufferDiv.innerHTML;
                        useLines.push(dataValue);
                        buffer = [];
                    }
                }
                for (let line of lines) {
                    if (line === progressLiteralStart) {
                        saveBuffer();
                        useLines.push({
                            type: "progress"
                        });
                    } else if (line.startsWith(promptLiteralStart)) {
                        saveBuffer();
                        const value = line.replace(promptLiteralStart, "").trimEnd();
                        useLines.push({
                            type: "input",
                            value: value
                        });
                    } else if (line.startsWith("// ")) {
                        saveBuffer();
                        const value = "💬 " + line.replace("// ", "").trimEnd();
                        useLines.push({
                            value: value,
                            class: "termynal-comment",
                            delay: 0
                        });
                    } else if (line.startsWith(customPromptLiteralStart)) {
                        saveBuffer();
                        const value = line.replace(customPromptLiteralStart, "").trimEnd();
                        useLines.push({
                            type: "input",
                            value: value,
                            prompt: customPromptLiteralStart
                        });
                    } else {
                        buffer.push(line);
                    }
                }
                saveBuffer();
                const div = document.createElement("div");
                div.classList.add("termynal-container");
                node.parentElement.parentElement.replaceChild(div, node.parentElement);
                const termynal = new Termynal(div, {
                    typeDelay: 40,
                    lineData: useLines,
                    noInit: true,
                    lineDelay: 500,
                    forwardButton: false,
                    restartButton: false
                });
                termynals.push(termynal);
            });
    }

    function loadVisibleTermynals() {
        termynals = termynals.filter(termynal => {
            if (termynal.container.getBoundingClientRect().top - innerHeight <= 0) {
                termynal.init();
                return false;
            }
            return true;
        });
    }

    // Use IntersectionObserver for more reliable loading
    function setupIntersectionObserver() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const termynal = termynals.find(t => t.container === entry.target);
                    if (termynal) {
                        termynal.init();
                        termynals = termynals.filter(t => t !== termynal);
                        observer.unobserve(entry.target);
                    }
                }
            });
        }, {
            rootMargin: '100px' // Start loading 100px before it comes into view
        });

        termynals.forEach(termynal => {
            observer.observe(termynal.container);
        });
    }

    window.addEventListener("scroll", loadVisibleTermynals);
    createTermynals();

    // Try both methods for better compatibility
    if ('IntersectionObserver' in window) {
        setupIntersectionObserver();
    } else {
        loadVisibleTermynals();
    }
}

// Setup restart buttons for Termynal instances
function setupTermynalRestartButtons() {
    // CLI terminal restart button
    const cliRestartBtn = document.getElementById('termynal-cli-restart');
    if (cliRestartBtn) {
        const cliTerminal = document.getElementById('termynal-cli');
        if (cliTerminal) {
            const termynalInstance = new Termynal(cliTerminal);
            cliRestartBtn.addEventListener('click', () => {
                // Clear and restart
                cliTerminal.innerHTML = cliTerminal.getAttribute('data-original-html') || cliTerminal.innerHTML;
                if (!cliTerminal.getAttribute('data-original-html')) {
                    cliTerminal.setAttribute('data-original-html', cliTerminal.innerHTML);
                }
                new Termynal(cliTerminal);
            });
        }
    }
}

// Initialize when DOM is ready
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
        setupTermynal();
        setupTermynalRestartButtons();
    });
} else {
    setupTermynal();
    setupTermynalRestartButtons();
}
