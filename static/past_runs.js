// Past Runs Page JavaScript

// Load runs when page loads
document.addEventListener('DOMContentLoaded', () => {
    loadAllRuns();
    setupModal();
});

// Setup modal
function setupModal() {
    const modal = document.getElementById('claimModal');
    const closeBtn = modal.querySelector('.close');
    
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    window.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Load all past runs
async function loadAllRuns() {
    try {
        const response = await fetch('/api/claims');
        const data = await response.json();
        
        const container = document.getElementById('runsContainer');
        
        if (data.runs.length === 0) {
            container.innerHTML = `
                <div class="no-runs">
                    <div class="no-runs-icon">📭</div>
                    <h3>No Previous Runs Found</h3>
                    <p>Process some claims to see results here.</p>
                    <a href="/" class="btn btn-primary" style="margin-top: 20px;">Go to Claim Processing</a>
                </div>
            `;
            return;
        }
        
        // Load full details for each run
        container.innerHTML = '';
        
        for (const run of data.runs) {
            await renderRunCard(run, container);
        }
        
    } catch (error) {
        console.error('Error loading runs:', error);
        document.getElementById('runsContainer').innerHTML = 
            '<p style="color: red; text-align: center;">Error loading past runs. Please try again.</p>';
    }
}

// Render a single run card
async function renderRunCard(runSummary, container) {
    try {
        // Fetch full run details
        const response = await fetch(`/api/results/${runSummary.run_id}`);
        const runData = await response.json();
        
        const runCard = document.createElement('div');
        runCard.className = 'run-card';
        runCard.dataset.runId = runSummary.run_id;
        
        const timestamp = new Date(runSummary.timestamp).toLocaleString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const stats = runSummary.statistics;
        
        runCard.innerHTML = `
            <div class="run-header">
                <div>
                    <div class="run-title">Run: ${runSummary.run_id}</div>
                    <div class="run-date">📅 ${timestamp}</div>
                </div>
                <button class="expand-toggle" onclick="toggleRunDetails('${runSummary.run_id}')">
                    Show Details ▼
                </button>
            </div>
            
            <div class="run-stats-grid">
                <div class="stat-box approved">
                    <div class="stat-value">${stats.approved || 0}</div>
                    <div class="stat-label">Approved</div>
                </div>
                <div class="stat-box denied">
                    <div class="stat-value">${stats.denied || 0}</div>
                    <div class="stat-label">Denied</div>
                </div>
                <div class="stat-box uncertain">
                    <div class="stat-value">${stats.uncertain || 0}</div>
                    <div class="stat-label">Uncertain</div>
                </div>
                <div class="stat-box accuracy">
                    <div class="stat-value">${(stats.accuracy * 100).toFixed(1)}%</div>
                    <div class="stat-label">Accuracy</div>
                </div>
            </div>
            
            <div class="run-details" id="details-${runSummary.run_id}">
                <h3 style="margin-bottom: 16px;">Claims Processed (${runData.statistics.total_claims})</h3>
                <div class="claims-list">
                    ${runData.results.map(result => renderClaimCard(result)).join('')}
                </div>
            </div>
        `;
        
        container.appendChild(runCard);
        
    } catch (error) {
        console.error(`Error loading run ${runSummary.run_id}:`, error);
    }
}

// Render a claim card
function renderClaimCard(result) {
    const decision = (result.llm_decision.decision || 'UNCERTAIN').toLowerCase();
    const confidence = result.llm_decision.confidence || 0;
    const explanation = result.llm_decision.explanation || 'No explanation provided';
    
    // Truncate explanation for card view
    const shortExplanation = explanation.length > 150 
        ? explanation.substring(0, 150) + '...' 
        : explanation;
    
    let matchBadge = '';
    if (result.matches_expected) {
        if (result.matches_expected.exact_match) {
            matchBadge = '<span style="color: #10b981; font-weight: 600;">✓ Exact Match</span>';
        } else if (result.matches_expected.acceptable_match) {
            matchBadge = '<span style="color: #f59e0b; font-weight: 600;">≈ Acceptable</span>';
        } else {
            matchBadge = '<span style="color: #ef4444; font-weight: 600;">✗ Mismatch</span>';
        }
    }
    
    const hasVerification = result.llm_decision.clinic_verification_enabled;
    const hasSearch = result.llm_decision.google_search_grounding && 
                     result.llm_decision.google_search_grounding.length > 0;
    
    return `
        <div class="claim-card ${decision}">
            <div class="claim-header">
                <div class="claim-number">Claim ${result.claim_number}</div>
                <div class="decision-badge ${decision}">${decision.toUpperCase()}</div>
            </div>
            
            <div class="claim-explanation">${shortExplanation}</div>
            
            <div class="claim-meta">
                <span>📊 ${(confidence * 100).toFixed(0)}% confident</span>
                ${matchBadge ? `<span>${matchBadge}</span>` : ''}
            </div>
            
            ${hasVerification ? '<div style="margin-top: 8px; font-size: 0.85rem; color: #6b7280;">🔍 Clinic verification enabled</div>' : ''}
            ${hasSearch ? '<div style="margin-top: 4px; font-size: 0.85rem; color: #3b82f6;">🌐 Google Search used</div>' : ''}
            
            <button class="view-full-btn" onclick='showClaimDetailsModal(${JSON.stringify(result).replace(/'/g, "&#39;")})'>
                View Full Details →
            </button>
        </div>
    `;
}

// Toggle run details
function toggleRunDetails(runId) {
    const detailsDiv = document.getElementById(`details-${runId}`);
    const button = event.target;
    
    if (detailsDiv.classList.contains('expanded')) {
        detailsDiv.classList.remove('expanded');
        button.textContent = 'Show Details ▼';
    } else {
        detailsDiv.classList.add('expanded');
        button.textContent = 'Hide Details ▲';
    }
}

// Show claim details in modal
function showClaimDetailsModal(result) {
    const modal = document.getElementById('claimModal');
    const modalBody = document.getElementById('modalBody');
    
    const decision = (result.llm_decision.decision || 'UNCERTAIN').toLowerCase();
    
    let detailsHTML = `
        <h2>Claim ${result.claim_number} - Detailed Analysis</h2>
        
        <div class="result-item ${decision}" style="margin-top: 20px;">
            <div class="result-header">
                <h3>Decision</h3>
                <span class="decision-badge ${decision}">${decision.toUpperCase()}</span>
            </div>
            <div class="result-content">
                <p><strong>Explanation:</strong> ${result.llm_decision.explanation}</p>
                ${result.llm_decision.confidence ? `
                    <p><strong>Confidence:</strong> ${(result.llm_decision.confidence * 100).toFixed(1)}%</p>
                ` : ''}
                ${result.llm_decision.policy_section ? `
                    <p><strong>Policy Section:</strong> ${result.llm_decision.policy_section}</p>
                ` : ''}
                ${result.llm_decision.compensation_amount ? `
                    <p><strong>Compensation:</strong> ${result.llm_decision.compensation_amount}</p>
                ` : ''}
            </div>
        </div>
    `;
    
    // Claim description
    if (result.claim_data && result.claim_data.description) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px;">
                <h3>Claim Description</h3>
                <p style="white-space: pre-wrap;">${result.claim_data.description}</p>
            </div>
        `;
    }
    
    // Reasoning steps
    if (result.llm_decision.reasoning_steps && result.llm_decision.reasoning_steps.length > 0) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px;">
                <h3>Reasoning Steps</h3>
                <ol>
                    ${result.llm_decision.reasoning_steps.map(step => `<li>${step}</li>`).join('')}
                </ol>
            </div>
        `;
    }
    
    // Google Search Results
    if (result.llm_decision.google_search_grounding && result.llm_decision.google_search_grounding.length > 0) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px; background: #f0f9ff; padding: 16px; border-radius: 8px;">
                <h3 style="color: #0369a1;">🌐 Google Search Results</h3>
        `;
        
        result.llm_decision.google_search_grounding.forEach((grounding, idx) => {
            detailsHTML += `<div style="margin-top: 12px;">`;
            
            if (grounding.search_queries && grounding.search_queries.length > 0) {
                detailsHTML += `
                    <p><strong>Search Queries:</strong></p>
                    <ul>
                        ${grounding.search_queries.map(q => `<li><code>${q}</code></li>`).join('')}
                    </ul>
                `;
            }
            
            if (grounding.grounding_chunks && grounding.grounding_chunks.length > 0) {
                detailsHTML += `
                    <p><strong>Sources Found (${grounding.grounding_chunks.length}):</strong></p>
                    <ul style="list-style: none; padding-left: 0;">
                `;
                grounding.grounding_chunks.forEach(chunk => {
                    if (chunk.uri) {
                        detailsHTML += `
                            <li style="margin: 8px 0; padding: 8px; background: white; border-radius: 4px;">
                                ${chunk.title ? `<strong>${chunk.title}</strong><br>` : ''}
                                <a href="${chunk.uri}" target="_blank" style="color: #0369a1; font-size: 0.9rem;">${chunk.uri}</a>
                            </li>
                        `;
                    }
                });
                detailsHTML += `</ul>`;
            }
            
            detailsHTML += `</div>`;
        });
        
        detailsHTML += `</div>`;
    }
    
    // Clinic verification
    if (result.llm_decision.clinic_verification) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px;">
                <h3>🏥 Clinic Verification</h3>
                <pre style="background: #f9fafb; padding: 12px; border-radius: 4px; overflow-x: auto;">${JSON.stringify(result.llm_decision.clinic_verification, null, 2)}</pre>
            </div>
        `;
    }
    
    // Fraud indicators
    if (result.llm_decision.fraud_indicators && result.llm_decision.fraud_indicators.length > 0) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px; background: #fef2f2; padding: 16px; border-radius: 8px;">
                <h4 style="color: #991b1b;">⚠️ Fraud Indicators</h4>
                <ul>
                    ${result.llm_decision.fraud_indicators.map(indicator => `<li>${indicator}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    // Image metadata
    if (result.image_metadata && result.image_metadata.length > 0) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px;">
                <h3>📄 Document Analysis</h3>
        `;
        
        result.image_metadata.forEach(img => {
            const metadata = img.metadata;
            detailsHTML += `
                <div style="background: #f9fafb; padding: 16px; border-radius: 8px; margin-top: 12px;">
                    <h4>${img.filename}</h4>
            `;
            
            if (metadata.document_type) {
                detailsHTML += `<p><strong>Type:</strong> ${metadata.document_type}</p>`;
            }
            
            if (metadata.language) {
                detailsHTML += `<p><strong>Language:</strong> ${metadata.language}</p>`;
            }
            
            if (metadata.authenticity_indicators) {
                const auth = metadata.authenticity_indicators;
                detailsHTML += `
                    <p><strong>Authenticity:</strong></p>
                    <ul>
                        <li>Signature: ${auth.has_signature ? '✓' : '✗'}</li>
                        <li>Official Stamp: ${auth.has_official_stamp ? '✓' : '✗'}</li>
                        <li>Letterhead: ${auth.has_letterhead ? '✓' : '✗'}</li>
                    </ul>
                `;
            }
            
            detailsHTML += `</div>`;
        });
        
        detailsHTML += `</div>`;
    }
    
    // Expected answer comparison
    if (result.expected_answer) {
        const match = result.matches_expected;
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px;">
                <h3>Expected Answer Comparison</h3>
                <p><strong>Expected:</strong> ${result.expected_answer.decision}</p>
                ${result.expected_answer.explanation ? `
                    <p><strong>Reason:</strong> ${result.expected_answer.explanation}</p>
                ` : ''}
                <p><strong>Actual:</strong> ${decision.toUpperCase()}</p>
                <p><strong>Match:</strong> 
                    ${match.exact_match ? 
                        '<span style="color: #10b981;">✓ Exact Match</span>' : 
                        match.acceptable_match ? 
                            '<span style="color: #f59e0b;">≈ Acceptable Match</span>' : 
                            '<span style="color: #ef4444;">✗ Mismatch</span>'
                    }
                </p>
            </div>
        `;
    }
    
    modalBody.innerHTML = detailsHTML;
    modal.style.display = 'block';
}
