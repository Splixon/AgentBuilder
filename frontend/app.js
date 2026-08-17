document.addEventListener('DOMContentLoaded', () => {
    // Initialise Lucide icons
    lucide.createIcons();

    // DOM Elements
    const promptInput = document.getElementById('prompt-input');
    const startBtn = document.getElementById('start-btn');
    const btnIcon = document.getElementById('btn-icon');
    const btnText = document.getElementById('btn-text');
    
    const activeRunBadge = document.getElementById('active-run-badge');
    const activeRunIdText = document.getElementById('active-run-id-text');
    
    // Agent status nodes
    const nodePlanner = document.getElementById('node-planner');
    const nodeArchitect = document.getElementById('node-architect');
    const nodeCoder = document.getElementById('node-coder');
    const nodeReviewer = document.getElementById('node-reviewer');
    
    const statusPlanner = document.getElementById('status-planner');
    const statusArchitect = document.getElementById('status-architect');
    const statusCoder = document.getElementById('status-coder');
    const statusReviewer = document.getElementById('status-reviewer');
    
    // Task panel details
    const architectPlanSection = document.getElementById('architect-plan-section');
    const planReviewSection = document.getElementById('plan-review-section');
    const editAppName = document.getElementById('edit-app-name');
    const editAppDesc = document.getElementById('edit-app-desc');
    const editAppTech = document.getElementById('edit-app-tech');
    const editAppFiles = document.getElementById('edit-app-files');
    const editAppFeatures = document.getElementById('edit-app-features');
    const approvePlanBtn = document.getElementById('approve-plan-btn');
    
    const planAppName = document.getElementById('plan-app-name');
    const planAppDesc = document.getElementById('plan-app-desc');
    const planAppTech = document.getElementById('plan-app-tech');
    const tasksChecklist = document.getElementById('tasks-checklist');
    
    // Terminals
    const consoleStream = document.getElementById('console-stream');
    const clearConsoleBtn = document.getElementById('clear-console-btn');
    const autoscrollChk = document.getElementById('autoscroll-chk');
    
    // File Tree Explorer
    const fileTree = document.getElementById('file-tree');
    const refreshFilesBtn = document.getElementById('refresh-files-btn');
    const activeFileTitle = document.getElementById('active-file-title');
    const codeViewer = document.getElementById('code-viewer');
    
    // Command runner
    const commandInput = document.getElementById('command-input');
    const runCmdBtn = document.getElementById('run-cmd-btn');
    const killCmdBtn = document.getElementById('kill-cmd-btn');
    const commandConsole = document.getElementById('command-console');
    
    // Sidebar history
    const historyList = document.getElementById('history-list');

    // Pipeline Flow Modal Elements
    const viewPipelineBtn = document.getElementById('view-pipeline-btn');
    const pipelineModal = document.getElementById('pipeline-modal');
    const closePipelineBtn = document.getElementById('close-pipeline-btn');
    const newSessionBtn = document.getElementById('new-session-btn');

    let currentRunId = null;
    let eventSource = null;
    let activeCmdController = null;

    // Load session history
    async function loadHistory() {
        try {
            const res = await fetch('/api/history');
            const data = await res.json();
            
            if (data.length === 0) {
                historyList.innerHTML = '<li class="empty-history">No runs in this session</li>';
                return;
            }
            
            historyList.innerHTML = '';
            data.forEach(run => {
                const li = document.createElement('li');
                li.className = `history-item ${run.run_id === currentRunId ? 'active' : ''}`;
                li.innerHTML = `
                    <div class="history-item-content" style="flex: 1; min-width: 0;">
                        <span class="history-prompt">${run.prompt}</span>
                        <div class="history-meta">
                            <span>ID: ${run.run_id}</span>
                            <span class="status-text">${run.status.toUpperCase()}</span>
                        </div>
                    </div>
                    <button class="btn-delete-session" title="Delete Session">
                        <i data-lucide="trash-2"></i>
                    </button>
                `;
                li.addEventListener('click', () => {
                    selectRun(run.run_id);
                });

                const deleteBtn = li.querySelector('.btn-delete-session');
                deleteBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (confirm(`Are you sure you want to delete session ${run.run_id}?`)) {
                        try {
                            const delRes = await fetch(`/api/run/${run.run_id}`, {
                                method: 'DELETE'
                            });
                            if (delRes.ok) {
                                if (currentRunId === run.run_id) {
                                    newSessionBtn.click();
                                } else {
                                    loadHistory();
                                }
                            } else {
                                alert("Failed to delete session.");
                            }
                        } catch (err) {
                            console.error("Error deleting session", err);
                            alert("Error deleting session: " + err.message);
                        }
                    }
                });

                historyList.appendChild(li);
            });
            lucide.createIcons();
        } catch (e) {
            console.error("Failed to load history", e);
        }
    }

    // Load file list from project
    async function loadProjectFiles() {
        try {
            const url = currentRunId ? `/api/project/files?run_id=${currentRunId}` : '/api/project/files';
            const res = await fetch(url);
            const files = await res.json();
            
            if (files.length === 0) {
                fileTree.innerHTML = '<li class="empty-tree">No files created yet.</li>';
                return;
            }
            
            fileTree.innerHTML = '';
            files.forEach(filepath => {
                const li = document.createElement('li');
                li.className = 'file-tree-item';
                
                // Set file icon based on extension
                let iconName = 'file';
                if (filepath.endsWith('.py')) iconName = 'terminal';
                else if (filepath.endsWith('.html')) iconName = 'code';
                else if (filepath.endsWith('.css')) iconName = 'palette';
                else if (filepath.endsWith('.js') || filepath.endsWith('.ts') || filepath.endsWith('.tsx')) iconName = 'file-code';
                
                li.innerHTML = `<i data-lucide="${iconName}"></i> <span>${filepath}</span>`;
                li.addEventListener('click', () => {
                    document.querySelectorAll('.file-tree-item').forEach(item => item.classList.remove('active'));
                    li.classList.add('active');
                    viewFile(filepath);
                });
                fileTree.appendChild(li);
            });
            lucide.createIcons();
        } catch (e) {
            console.error("Failed to load project files", e);
        }
    }

    // View file content with syntax highlighting
    async function viewFile(filepath) {
        try {
            activeFileTitle.textContent = filepath;
            codeViewer.textContent = "Loading file content...";
            Prism.highlightElement(codeViewer);
            
            const url = currentRunId ? `/api/project/file/${encodeURIComponent(filepath)}?run_id=${currentRunId}` : `/api/project/file/${encodeURIComponent(filepath)}`;
            const res = await fetch(url);
            if (!res.ok) {
                throw new Error("File not found or unreachable");
            }
            const data = await res.json();
            
            // Set prism language class based on file extension
            let langClass = 'language-javascript';
            if (filepath.endsWith('.py')) langClass = 'language-python';
            else if (filepath.endsWith('.css')) langClass = 'language-css';
            else if (filepath.endsWith('.html')) langClass = 'language-markup';
            
            codeViewer.className = langClass;
            codeViewer.textContent = data.content || "// Empty file";
            Prism.highlightElement(codeViewer);
        } catch (e) {
            codeViewer.textContent = `Error loading file: ${e.message}`;
            codeViewer.className = 'language-javascript';
            Prism.highlightElement(codeViewer);
        }
    }

    // Log printer helper
    function appendLog(message, type = 'log') {
        const line = document.createElement('div');
        line.className = `console-line ${type}-line`;
        line.textContent = message;
        consoleStream.appendChild(line);
        
        if (autoscrollChk.checked) {
            consoleStream.scrollTop = consoleStream.scrollHeight;
        }
    }

    // Reset pipeline node UI
    function resetPipelineUI() {
        const statuses = [statusPlanner, statusArchitect, statusCoder, statusReviewer];
        const nodes = [nodePlanner, nodeArchitect, nodeCoder, nodeReviewer];
        
        statuses.forEach(s => {
            s.className = 'node-status status-idle';
            s.textContent = 'Idle';
        });
        
        nodes.forEach(n => {
            n.className = 'pipeline-node';
        });
    }

    // Update specific pipeline agent node UI status
    function setNodeStatus(nodeId, statusStr) {
        const node = document.getElementById(`node-${nodeId}`);
        const status = document.getElementById(`status-${nodeId}`);
        if (!node || !status) return;

        // Clean classes
        node.className = 'pipeline-node';
        status.className = 'node-status';

        if (statusStr === 'active') {
            node.classList.add('active');
            status.classList.add('status-active');
            status.textContent = 'Executing';
        } else if (statusStr === 'done') {
            node.classList.add('completed');
            status.classList.add('status-done');
            status.textContent = 'Completed';
        } else if (statusStr === 'failed') {
            node.classList.add('failed');
            status.classList.add('status-failed');
            status.textContent = 'Failed';
        } else {
            status.classList.add('status-idle');
            status.textContent = 'Idle';
        }
    }

    // Select run and subscribe
    function selectRun(runId) {
        if (eventSource) {
            eventSource.close();
        }

        currentRunId = runId;
        activeRunBadge.classList.remove('hidden');
        activeRunIdText.textContent = `RUN-ID: ${runId}`;
        
        // Clear checklists, logs, UI
        resetPipelineUI();
        architectPlanSection.classList.add('hidden');
        planReviewSection.classList.add('hidden');
        tasksChecklist.innerHTML = '';
        consoleStream.innerHTML = '';
        
        loadHistory();

        // Connect SSE stream
        appendLog(`[SYSTEM] Subscribing to stream for run ${runId}...`, 'system');
        eventSource = new EventSource(`/api/stream/${runId}`);

        eventSource.onerror = (err) => {
            console.error("SSE stream error", err);
            appendLog("[SYSTEM] SSE connection closed or encountered error.", 'error');
            eventSource.close();
            setButtonRunningState(false);
        };

        eventSource.addEventListener('status', (e) => {
            const data = JSON.parse(e.data);
            appendLog(`[SYSTEM] Run status: ${data.status.toUpperCase()}`, 'system');
            
            if (data.status === 'planning') {
                resetPipelineUI();
                setNodeStatus('planner', 'active');
                setButtonRunningState(true);
            } else if (data.status === 'awaiting_plan_approval') {
                setNodeStatus('planner', 'done');
                appendLog("[SYSTEM] Awaiting plan review and approval in UI...", 'system');
            } else if (data.status === 'architecting') {
                setNodeStatus('planner', 'done');
                setNodeStatus('architect', 'active');
                planReviewSection.classList.add('hidden');
            } else if (data.status === 'coding') {
                setNodeStatus('planner', 'done');
                setNodeStatus('architect', 'done');
                setNodeStatus('coder', 'active');
            } else if (data.status === 'reviewing') {
                setNodeStatus('planner', 'done');
                setNodeStatus('architect', 'done');
                setNodeStatus('coder', 'done');
                setNodeStatus('reviewer', 'active');
            } else if (data.status === 'completed') {
                setNodeStatus('planner', 'done');
                setNodeStatus('architect', 'done');
                setNodeStatus('coder', 'done');
                setNodeStatus('reviewer', 'done');
                appendLog("[SYSTEM] Execution finished successfully!", 'success');
                setButtonRunningState(false);
                loadProjectFiles();
                loadHistory();
            } else if (data.status === 'failed') {
                setNodeStatus('coder', 'failed');
                setNodeStatus('reviewer', 'failed');
                appendLog("[SYSTEM] Execution failed.", 'error');
                setButtonRunningState(false);
                loadHistory();
            }
        });

        eventSource.addEventListener('planner_result', (e) => {
            const data = JSON.parse(e.data);
            
            // Populate Form inputs
            editAppName.value = data.name || '';
            editAppDesc.value = data.description || '';
            editAppTech.value = data.techstack || '';
            editAppFiles.value = data.files ? data.files.map(f => f.path).join(', ') : '';
            editAppFeatures.value = data.features ? data.features.join('\n') : '';

            // Show Form & Hide Checklist
            planReviewSection.classList.remove('hidden');
            architectPlanSection.classList.add('hidden');
            
            appendLog(`[PLANNER] Plan generated for: ${data.name}. Stack: ${data.techstack}. Awaiting user approval.`, 'success');
        });

        eventSource.addEventListener('architect_result', (e) => {
            const data = JSON.parse(e.data);
            tasksChecklist.innerHTML = '';
            
            data.implementation_steps.forEach((step, idx) => {
                const item = document.createElement('div');
                item.className = 'task-item';
                item.id = `task-step-${idx}`;
                item.innerHTML = `
                    <input type="checkbox" class="task-checkbox" disabled id="chk-step-${idx}">
                    <div class="task-details">
                        <span class="task-desc">${step.task_description}</span>
                        <div class="task-file">File: ${step.filepath}</div>
                    </div>
                `;
                tasksChecklist.appendChild(item);
            });
            appendLog(`[ARCHITECT] Created ${data.implementation_steps.length} tasks.`, 'success');
        });

        eventSource.addEventListener('coder_step_start', (e) => {
            const data = JSON.parse(e.data);
            const items = document.querySelectorAll('.task-item');
            
            items.forEach(item => item.classList.remove('active'));
            
            const activeItem = document.getElementById(`task-step-${data.step_idx}`);
            if (activeItem) {
                activeItem.classList.add('active');
                
                // scroll into view
                activeItem.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            
            // Mark previous steps as checked
            for (let i = 0; i < data.step_idx; i++) {
                const chk = document.getElementById(`chk-step-${i}`);
                const pItem = document.getElementById(`task-step-${i}`);
                if (chk) chk.checked = true;
                if (pItem) pItem.classList.add('completed');
            }
            
            appendLog(`[CODER] Implementing Task ${data.step_idx + 1}/${data.total_steps}: editing ${data.filepath}`, 'tool');
        });

        eventSource.addEventListener('file_written', (e) => {
            const data = JSON.parse(e.data);
            appendLog(`[CODER] File written: ${data.path}`, 'success');
            loadProjectFiles();
        });

        eventSource.addEventListener('command_start', (e) => {
            const data = JSON.parse(e.data);
            appendLog(`[COMMAND] Executing verification: ${data.command}`, 'tool');
        });

        eventSource.addEventListener('command_end', (e) => {
            const data = JSON.parse(e.data);
            appendLog(`[COMMAND] Command finished with exit code ${data.returncode}.`, data.returncode === 0 ? 'success' : 'error');
            if (data.stdout) {
                appendLog(`Stdout:\n${data.stdout.trim()}`, 'log');
            }
            if (data.stderr) {
                appendLog(`Stderr:\n${data.stderr.trim()}`, 'error');
            }
        });

        eventSource.addEventListener('log', (e) => {
            const data = JSON.parse(e.data);
            let type = 'log';
            if (data.message.includes('[ERROR]')) type = 'error';
            else if (data.message.includes('[WARNING]')) type = 'system';
            appendLog(data.message, type);
        });

        eventSource.addEventListener('reviewer_feedback', (e) => {
            const data = JSON.parse(e.data);
            if (!data.is_correct) {
                appendLog(`[QA REVIEWER] Bugs detected in verification (QA Loop #${data.review_count})! File to fix: ${data.filepath}. Description: ${data.description}`, 'error');
                
                // Append the bugfix task to the checklist in the UI
                const idx = data.next_step;
                const item = document.createElement('div');
                item.className = 'task-item active';
                item.id = `task-step-${idx}`;
                item.innerHTML = `
                    <input type="checkbox" class="task-checkbox" disabled id="chk-step-${idx}">
                    <div class="task-details">
                        <span class="task-desc">Fix bug: ${data.description}</span>
                        <div class="task-file">File: ${data.filepath}</div>
                    </div>
                `;
                tasksChecklist.appendChild(item);
                item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            } else {
                appendLog(`[QA REVIEWER] Verification passed (QA Loop #${data.review_count}): ${data.description}`, 'success');
            }
        });
    }

    function setButtonRunningState(running) {
        if (running) {
            startBtn.classList.add('btn-outline');
            startBtn.classList.remove('btn-primary');
            btnIcon.setAttribute('data-lucide', 'loader');
            btnText.textContent = "Running Agent...";
            startBtn.disabled = true;
        } else {
            startBtn.classList.remove('btn-outline');
            startBtn.classList.add('btn-primary');
            btnIcon.setAttribute('data-lucide', 'play');
            btnText.textContent = "Generate Project";
            startBtn.disabled = false;
        }
        lucide.createIcons();
    }

    // Trigger new agent run
    startBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            alert("Please enter a project description.");
            return;
        }

        try {
            setButtonRunningState(true);
            appendLog("[SYSTEM] Initiating backend run...", 'system');
            
            const res = await fetch('/api/run', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });

            if (!res.ok) throw new Error("HTTP error starting agent");
            const data = await res.json();
            
            selectRun(data.run_id);
        } catch (e) {
            appendLog(`[ERROR] Failed to start run: ${e.message}`, 'error');
            setButtonRunningState(false);
        }
    });

    approvePlanBtn.addEventListener('click', async () => {
        if (!currentRunId) return;
        
        approvePlanBtn.disabled = true;
        const originalText = approvePlanBtn.innerHTML;
        approvePlanBtn.textContent = "Submitting Plan Approval...";

        const files = editAppFiles.value.split(',')
            .map(f => f.trim())
            .filter(f => f.length > 0)
            .map(f => ({ path: f, purpose: "User defined" }));

        const features = editAppFeatures.value.split('\n')
            .map(f => f.trim())
            .filter(f => f.length > 0);

        const payload = {
            plan: {
                name: editAppName.value.trim(),
                description: editAppDesc.value.trim(),
                techstack: editAppTech.value.trim(),
                files: files,
                features: features
            }
        };

        try {
            const res = await fetch(`/api/run/${currentRunId}/approve`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error("Approval request failed");
            
            appendLog("[SYSTEM] Plan approved by user. Architecting and Code generation starting...", 'system');
            planReviewSection.classList.add('hidden');
            
            // Render the edited metadata in checklist section
            architectPlanSection.classList.remove('hidden');
            planAppName.textContent = payload.plan.name;
            planAppDesc.textContent = payload.plan.description;
            planAppTech.textContent = payload.plan.techstack;
        } catch (e) {
            appendLog(`[ERROR] Failed to approve plan: ${e.message}`, 'error');
            approvePlanBtn.disabled = false;
            approvePlanBtn.innerHTML = originalText;
            lucide.createIcons();
        } finally {
            approvePlanBtn.disabled = false;
            approvePlanBtn.innerHTML = `
                <i data-lucide="check"></i>
                <span>Approve Plan & Craft Code</span>
            `;
            lucide.createIcons();
        }
    });

    // Clear execution console logs
    clearConsoleBtn.addEventListener('click', () => {
        consoleStream.innerHTML = '';
    });

    // Refresh project files tree manually
    refreshFilesBtn.addEventListener('click', loadProjectFiles);

    // Command console helper
    function appendCmdLog(text, type = 'stdout') {
        const line = document.createElement('div');
        line.className = `cmd-line cmd-${type}`;
        line.textContent = text;
        commandConsole.appendChild(line);
        commandConsole.scrollTop = commandConsole.scrollHeight;
    }

    // Custom commands runner
    runCmdBtn.addEventListener('click', async () => {
        const command = commandInput.value.trim();
        if (!command) return;

        runCmdBtn.classList.add('hidden');
        killCmdBtn.classList.remove('hidden');
        commandInput.disabled = true;
        appendCmdLog(`> ${command}`, 'system');

        activeCmdController = new AbortController();
        const signal = activeCmdController.signal;

        try {
            const response = await fetch('/api/project/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command, run_id: currentRunId }),
                signal
            });

            const reader = response.body.getReader();
            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const text = decoder.decode(value);
                const lines = text.split('\n\n');
                lines.forEach(line => {
                    if (line.startsWith('data: ')) {
                        const content = line.substring(6).trim();
                        if (content.startsWith('stdout: ')) {
                            appendCmdLog(content.substring(8), 'stdout');
                        } else if (content.startsWith('stderr: ')) {
                            appendCmdLog(content.substring(8), 'stderr');
                        } else if (content.startsWith('error: ')) {
                            appendCmdLog(content.substring(7), 'stderr');
                        } else if (content) {
                            appendCmdLog(content, 'stdout');
                        }
                    }
                });
            }
            appendCmdLog(`[Process Exited]`, 'system');
        } catch (e) {
            if (e.name === 'AbortError') {
                appendCmdLog(`[Process Terminated by User]`, 'system');
            } else {
                appendCmdLog(`Error executing command: ${e.message}`, 'stderr');
            }
        } finally {
            runCmdBtn.classList.remove('hidden');
            killCmdBtn.classList.add('hidden');
            commandInput.disabled = false;
            activeCmdController = null;
        }
    });

    // Abort running command
    killCmdBtn.addEventListener('click', () => {
        if (activeCmdController) {
            activeCmdController.abort();
        }
    });

    // Run command on hitting Enter in input
    commandInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            runCmdBtn.click();
        }
    });

    // Pipeline Flow Modal Events
    if (viewPipelineBtn && pipelineModal && closePipelineBtn) {
        viewPipelineBtn.addEventListener('click', () => {
            pipelineModal.classList.remove('hidden');
            // Re-create icons to ensure lucide icons inside the modal are loaded
            lucide.createIcons();
        });

        closePipelineBtn.addEventListener('click', () => {
            pipelineModal.classList.add('hidden');
        });

        pipelineModal.addEventListener('click', (e) => {
            if (e.target === pipelineModal) {
                pipelineModal.classList.add('hidden');
            }
        });
    }

    // New Session button logic
    if (newSessionBtn) {
        newSessionBtn.addEventListener('click', () => {
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
            currentRunId = null;
            activeRunBadge.classList.add('hidden');
            activeRunIdText.textContent = 'RUN-ID: None';
            
            promptInput.value = '';
            promptInput.disabled = false;
            startBtn.disabled = false;
            btnText.textContent = 'Start Agent Pipeline';
            btnIcon.setAttribute('data-lucide', 'play');
            lucide.createIcons();
            
            resetPipelineUI();
            
            architectPlanSection.classList.add('hidden');
            planReviewSection.classList.add('hidden');
            tasksChecklist.innerHTML = '';
            
            fileTree.innerHTML = '<li class="empty-tree">No files created yet.</li>';
            codeViewer.textContent = "// Empty file";
            activeFileTitle.textContent = "No file selected";
            
            consoleStream.innerHTML = '';
            appendLog('--- Started New Session ---', 'system');
            
            loadHistory();
        });
    }

    // Initial load
    loadHistory();
    loadProjectFiles();
});
