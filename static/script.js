// Global state
let selectedClaims = new Set();
let availableClaims = [];
let currentResults = null;

// Initialize app when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    loadAvailableClaims();
    setupEventListeners();
    
    // Check if we should load a specific run (coming from past runs page)
    const urlParams = new URLSearchParams(window.location.search);
    const runId = urlParams.get('view') || sessionStorage.getItem('viewRunId');
    if (runId) {
        sessionStorage.removeItem('viewRunId');
        loadRunDetails(runId);
    }
});

// Setup event listeners
function setupEventListeners() {
    document.getElementById('selectAllBtn').addEventListener('click', selectAllClaims);
    document.getElementById('clearAllBtn').addEventListener('click', clearAllClaims);
    document.getElementById('processBtn').addEventListener('click', processClaims);
    
    // Modal close
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

// Load available claims
async function loadAvailableClaims() {
    try {
        const response = await fetch('/api/claims/available');
        const data = await response.json();
        
        availableClaims = data.available_claims;
        renderClaimGrid();
        
    } catch (error) {
        console.error('Error loading claims:', error);
        showError('Failed to load available claims');
    }
}

// Render claim grid
function renderClaimGrid() {
    const grid = document.getElementById('claimGrid');
    grid.innerHTML = '';
    
    availableClaims.forEach(claimNum => {
        const claimItem = document.createElement('div');
        claimItem.className = 'claim-item';
        claimItem.dataset.claimNumber = claimNum;
        
        claimItem.innerHTML = `
            <div class="claim-number">Claim ${claimNum}</div>
            <div class="claim-status">Click to select</div>
        `;
        
        claimItem.addEventListener('click', () => toggleClaim(claimNum));
        grid.appendChild(claimItem);
    });
}

// Toggle claim selection
function toggleClaim(claimNum) {
    if (selectedClaims.has(claimNum)) {
        selectedClaims.delete(claimNum);
    } else {
        selectedClaims.add(claimNum);
    }
    
    updateClaimSelection();
}

// Update visual selection state
function updateClaimSelection() {
    // Update visual state
    document.querySelectorAll('.claim-item').forEach(item => {
        const claimNum = parseInt(item.dataset.claimNumber);
        if (selectedClaims.has(claimNum)) {
            item.classList.add('selected');
        } else {
            item.classList.remove('selected');
        }
    });
    
    // Update counter
    document.getElementById('selectionCount').textContent = 
        `${selectedClaims.size} claim${selectedClaims.size !== 1 ? 's' : ''} selected`;
    
    // Enable/disable process button
    document.getElementById('processBtn').disabled = selectedClaims.size === 0;
}

// Select all claims
function selectAllClaims() {
    selectedClaims = new Set(availableClaims);
    updateClaimSelection();
}

// Clear all claims
function clearAllClaims() {
    selectedClaims.clear();
    updateClaimSelection();
}

// Process selected claims
async function processClaims() {
    if (selectedClaims.size === 0) return;
    
    const processBtn = document.getElementById('processBtn');
    const btnText = processBtn.querySelector('.btn-text');
    const btnLoader = processBtn.querySelector('.btn-loader');
    
    // Get clinic verification toggle state
    const clinicVerificationEnabled = document.getElementById('clinicVerificationToggle').checked;
    
    // Show loading state
    processBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';
    
    // Hide previous results
    document.getElementById('resultsSection').style.display = 'none';
    
    try {
        const response = await fetch('/api/claims/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                claim_numbers: Array.from(selectedClaims).sort((a, b) => a - b),
                enable_clinic_verification: clinicVerificationEnabled
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to process claims');
        }
        
        const data = await response.json();
        currentResults = data.summary;
        
        // Show results
        displayResults(data.summary);
        
        // Show success message with verification status
        let message = `Successfully processed ${selectedClaims.size} claims!`;
        if (clinicVerificationEnabled && data.clinic_verification_used) {
            message += ' (Clinic verification enabled)';
        }
        showSuccess(message);
        
    } catch (error) {
        console.error('Error processing claims:', error);
        showError('Failed to process claims. Please check your API key and try again.');
    } finally {
        // Reset button state
        processBtn.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
}

// Display results
function displayResults(summary) {
    const resultsSection = document.getElementById('resultsSection');
    const summaryDiv = document.getElementById('resultsSummary');
    const resultsGrid = document.getElementById('resultsGrid');
    
    // Show section
    resultsSection.style.display = 'block';
    
    // Render summary stats
    const stats = summary.statistics;
    summaryDiv.innerHTML = `
        <div class="stat-card approve">
            <div class="stat-value">${stats.approved}</div>
            <div class="stat-label">Approved</div>
        </div>
        <div class="stat-card deny">
            <div class="stat-value">${stats.denied}</div>
            <div class="stat-label">Denied</div>
        </div>
        <div class="stat-card uncertain">
            <div class="stat-value">${stats.uncertain}</div>
            <div class="stat-label">Uncertain</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${(stats.accuracy * 100).toFixed(1)}%</div>
            <div class="stat-label">Accuracy</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.exact_matches}</div>
            <div class="stat-label">Exact Matches</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${stats.acceptable_matches}</div>
            <div class="stat-label">Acceptable</div>
        </div>
    `;
    
    // Render individual results
    resultsGrid.innerHTML = '';
    summary.results.forEach(result => {
        const decision = result.llm_decision.decision || 'UNCERTAIN';
        const resultItem = document.createElement('div');
        resultItem.className = `result-item ${decision.toLowerCase()}`;
        
        const confidence = result.llm_decision.confidence || 0;
        const match = result.matches_expected;
        
        let matchIndicator = '';
        if (match) {
            if (match.exact_match) {
                matchIndicator = '<span style="color: #10b981;">✓ Exact Match</span>';
            } else if (match.acceptable_match) {
                matchIndicator = '<span style="color: #f59e0b;">≈ Acceptable</span>';
            } else {
                matchIndicator = '<span style="color: #ef4444;">✗ Mismatch</span>';
            }
        }
        
        // Check if Google Search was used
        let searchIndicator = '';
        if (result.llm_decision.clinic_verification_enabled && result.llm_decision.google_search_grounding && result.llm_decision.google_search_grounding.length > 0) {
            const totalSources = result.llm_decision.google_search_grounding.reduce((sum, g) => 
                sum + (g.total_sources || 0), 0
            );
            searchIndicator = `<span style="color: #10b981; font-size: 0.85rem;">🔍 Verified with ${totalSources} source(s)</span>`;
        } else if (result.llm_decision.clinic_verification_enabled) {
            searchIndicator = `<span style="color: #64748b; font-size: 0.85rem;">🔍 Verification enabled</span>`;
        }
        
        resultItem.innerHTML = `
            <div class="result-header">
                <h3>Claim ${result.claim_number}</h3>
                <span class="decision-badge ${decision.toLowerCase()}">${decision}</span>
            </div>
            <div class="result-content">
                <div class="explanation">${result.llm_decision.explanation || 'No explanation provided'}</div>
                <div class="metadata">
                    <div class="metadata-item">
                        <strong>Confidence:</strong> ${(confidence * 100).toFixed(1)}%
                    </div>
                    ${result.llm_decision.compensation_amount ? `
                        <div class="metadata-item">
                            <strong>Compensation:</strong> ${result.llm_decision.compensation_amount}
                        </div>
                    ` : ''}
                    ${matchIndicator ? `
                        <div class="metadata-item">
                            ${matchIndicator}
                        </div>
                    ` : ''}
                    ${searchIndicator ? `
                        <div class="metadata-item">
                            ${searchIndicator}
                        </div>
                    ` : ''}
                </div>
                ${confidence > 0 ? `
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${confidence * 100}%"></div>
                    </div>
                ` : ''}
            </div>
        `;
        
        resultItem.addEventListener('click', () => showClaimDetails(result));
        resultsGrid.appendChild(resultItem);
    });
    
    // Scroll to results
    resultsSection.scrollIntoView({ behavior: 'smooth' });
}

// Show detailed claim view
function showClaimDetails(result) {
    const modal = document.getElementById('claimModal');
    const modalBody = document.getElementById('modalBody');
    
    const decision = result.llm_decision.decision || 'UNCERTAIN';
    
    let detailsHTML = `
        <h2>Claim ${result.claim_number} - Detailed Analysis</h2>
        
        <div class="result-item ${decision.toLowerCase()}" style="margin-top: 20px;">
            <div class="result-header">
                <h3>Decision</h3>
                <span class="decision-badge ${decision.toLowerCase()}">${decision}</span>
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
                    <p><strong>Compensation Amount:</strong> ${result.llm_decision.compensation_amount}</p>
                ` : ''}
            </div>
        </div>
    `;
    
    // Claim description
    if (result.claim_data.description) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px;">
                <h3>Claim Description</h3>
                <p>${result.claim_data.description}</p>
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
    
    // Fraud indicators
    if (result.llm_decision.fraud_indicators && result.llm_decision.fraud_indicators.length > 0) {
        detailsHTML += `
            <div class="fraud-indicator" style="margin-top: 20px;">
                <h4>⚠️ Fraud Indicators</h4>
                <ul>
                    ${result.llm_decision.fraud_indicators.map(indicator => `<li>${indicator}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    // Clinic verification results (old format - from custom function calls)
    if (result.llm_decision.clinic_verification && result.llm_decision.clinic_verification.length > 0) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px; padding: 15px; background: #f0f9ff; border-radius: 8px;">
                <h3>🔍 Clinic Verification Results</h3>
        `;
        
        result.llm_decision.clinic_verification.forEach(verification => {
            const result_data = verification.result;
            const verified = result_data.verified;
            const confidence = result_data.confidence || 0;
            
            let statusColor = verified === true ? '#10b981' : verified === false ? '#ef4444' : '#f59e0b';
            let statusIcon = verified === true ? '✓' : verified === false ? '✗' : '⚠';
            let statusText = verified === true ? 'Verified' : verified === false ? 'Not Found' : 'Unknown';
            
            detailsHTML += `
                <div style="margin: 10px 0; padding: 10px; background: white; border-radius: 4px;">
                    <p><strong>Facility:</strong> ${verification.arguments.facility_name}</p>
                    ${verification.arguments.location ? `<p><strong>Location:</strong> ${verification.arguments.location}</p>` : ''}
                    <p><strong>Status:</strong> <span style="color: ${statusColor}; font-weight: bold;">${statusIcon} ${statusText}</span></p>
                    <p><strong>Confidence:</strong> ${(confidence * 100).toFixed(0)}%</p>
                    <p><strong>Message:</strong> ${result_data.message}</p>
                    
                    ${result_data.search_results && result_data.search_results.length > 0 ? `
                        <details style="margin-top: 10px;">
                            <summary style="cursor: pointer; color: #3b82f6;">View Search Results</summary>
                            <ul style="margin-top: 10px;">
                                ${result_data.search_results.map(sr => `
                                    <li style="margin: 8px 0;">
                                        <a href="${sr.link}" target="_blank" style="color: #3b82f6;">${sr.title}</a>
                                        <p style="font-size: 0.9rem; color: #64748b; margin: 4px 0 0 0;">${sr.snippet}</p>
                                    </li>
                                `).join('')}
                            </ul>
                        </details>
                    ` : ''}
                </div>
            `;
        });
        
        detailsHTML += `</div>`;
    }
    
    // Google Search Grounding results
    if (result.llm_decision.google_search_grounding && result.llm_decision.google_search_grounding.length > 0) {
        detailsHTML += `
            <div class="google-search-section" style="margin-top: 20px; padding: 20px; background: #e0f2fe; border-left: 4px solid #0284c7; border-radius: 4px;">
                <h3 style="color: #0284c7; margin-top: 0;">🔍 Google Search Results</h3>
                <p style="color: #64748b;">The LLM used Google Search to verify information in this claim.</p>
        `;
        
        result.llm_decision.google_search_grounding.forEach((grounding, idx) => {
            if (grounding.search_performed) {
                detailsHTML += `<div style="margin: 15px 0; padding: 12px; background: white; border-radius: 6px;">`;
                detailsHTML += `<h4 style="margin: 0 0 10px 0; color: #10b981;">Search Session ${idx + 1}</h4>`;
                
                // Show search entry point if available
                if (grounding.search_entry_point) {
                    detailsHTML += `
                        <p style="font-size: 0.9rem; color: #64748b; margin-bottom: 10px;">
                            <strong>Search Query:</strong> ${grounding.search_entry_point.rendered_content || 'N/A'}
                        </p>
                    `;
                }
                
                // Show grounding chunks (search results)
                if (grounding.grounding_chunks && grounding.grounding_chunks.length > 0) {
                    detailsHTML += `
                        <p style="margin: 10px 0 5px 0;"><strong>Sources Found (${grounding.total_sources || grounding.grounding_chunks.length}):</strong></p>
                        <ul style="list-style: none; padding: 0; margin: 10px 0;">
                    `;
                    
                    grounding.grounding_chunks.forEach((chunk, chunkIdx) => {
                        detailsHTML += `
                            <li style="margin: 8px 0; padding: 10px; background: #f8fafc; border-left: 3px solid #10b981; border-radius: 4px;">
                                <div style="font-weight: 500; color: #1e293b; margin-bottom: 4px;">
                                    ${chunk.title || `Source ${chunkIdx + 1}`}
                                </div>
                                ${chunk.uri ? `
                                    <a href="${chunk.uri}" target="_blank" style="color: #3b82f6; font-size: 0.85rem; word-break: break-all;">
                                        ${chunk.uri}
                                    </a>
                                ` : ''}
                            </li>
                        `;
                    });
                    
                    detailsHTML += `</ul>`;
                }
                
                // Show grounding supports (which parts of the response used search)
                if (grounding.grounding_support && grounding.grounding_support.length > 0) {
                    detailsHTML += `
                        <details style="margin-top: 12px;">
                            <summary style="cursor: pointer; color: #3b82f6; font-size: 0.9rem;">
                                📝 View claims backed by search (${grounding.grounding_support.length})
                            </summary>
                            <div style="margin-top: 10px; padding-left: 10px;">
                    `;
                    
                    grounding.grounding_support.forEach((support, supportIdx) => {
                        if (support.text) {
                            const sourceIndices = support.chunk_indices ? 
                                support.chunk_indices.map(i => i + 1).join(', ') : 'N/A';
                            detailsHTML += `
                                <div style="margin: 8px 0; padding: 8px; background: #fefce8; border-left: 3px solid #eab308; border-radius: 4px;">
                                    <p style="margin: 0 0 4px 0; font-size: 0.9rem;">"${support.text}"</p>
                                    <p style="margin: 0; font-size: 0.8rem; color: #64748b;">
                                        Supported by source(s): ${sourceIndices}
                                    </p>
                                </div>
                            `;
                        }
                    });
                    
                    detailsHTML += `
                            </div>
                        </details>
                    `;
                }
                
                detailsHTML += `</div>`;
            }
        });
        
        detailsHTML += `</div>`;
    }
    
    // Image metadata
    if (result.image_metadata && result.image_metadata.length > 0) {
        detailsHTML += `
            <div class="preview-section" style="margin-top: 20px;">
                <h3>Document Analysis</h3>
        `;
        
        result.image_metadata.forEach(img => {
            const metadata = img.metadata;
            detailsHTML += `
                <div class="image-metadata">
                    <h4>📄 ${img.filename}</h4>
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
                        ${auth.quality_assessment ? `<li>Quality: ${auth.quality_assessment}</li>` : ''}
                    </ul>
                `;
            }
            
            if (metadata.key_information) {
                detailsHTML += `<p><strong>Key Information:</strong></p>`;
                detailsHTML += `<pre>${JSON.stringify(metadata.key_information, null, 2)}</pre>`;
            }
            
            if (metadata.text_content) {
                detailsHTML += `
                    <p><strong>Extracted Text:</strong></p>
                    <div style="background: white; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto;">
                        <pre style="white-space: pre-wrap; font-size: 0.9rem;">${metadata.text_content}</pre>
                    </div>
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
                    <p><strong>Expected Explanation:</strong> ${result.expected_answer.explanation}</p>
                ` : ''}
                <p><strong>Actual:</strong> ${decision}</p>
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

// Load run details
async function loadRunDetails(runId) {
    try {
        const response = await fetch(`/api/results/${runId}`);
        const data = await response.json();
        
        displayResults(data);
        
    } catch (error) {
        console.error('Error loading run details:', error);
        showError('Failed to load run details');
    }
}

// Show success message
function showSuccess(message) {
    // Simple implementation - could be enhanced with a toast library
    alert('✓ ' + message);
}

// Show error message
function showError(message) {
    alert('✗ ' + message);
}
