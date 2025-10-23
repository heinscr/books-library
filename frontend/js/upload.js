/**
 * Upload module
 * Handles book upload functionality
 */

let selectedFile = null;

function showUploadModal() {
    // Check if user is admin
    if (!window.isUserAdmin) {
        showAlert('❌ Only administrators can upload books', 'error');
        return;
    }
    
    document.getElementById('uploadModal').style.display = 'flex';
    // Reset form
    document.getElementById('bookFile').value = '';
    document.getElementById('authorName').value = '';
    document.getElementById('fileInfo').classList.remove('show');
    document.getElementById('uploadButton').disabled = true;
    document.getElementById('uploadProgress').style.display = 'none';
    selectedFile = null;
}

function closeUploadModal() {
    document.getElementById('uploadModal').style.display = 'none';
}

function handleFileSelect() {
    const fileInput = document.getElementById('bookFile');
    const fileInfo = document.getElementById('fileInfo');
    const uploadButton = document.getElementById('uploadButton');
    
    if (fileInput.files.length > 0) {
        selectedFile = fileInput.files[0];
        
        // Validate file type
        if (!selectedFile.name.toLowerCase().endsWith('.zip')) {
            showAlert('❌ Please select a .zip file', 'error');
            fileInput.value = '';
            selectedFile = null;
            uploadButton.disabled = true;
            fileInfo.classList.remove('show');
            return;
        }
        
        // Validate file size (5GB max)
        const maxSize = 5 * 1024 * 1024 * 1024; // 5GB in bytes
        if (selectedFile.size > maxSize) {
            showAlert('❌ File size exceeds 5GB limit', 'error');
            fileInput.value = '';
            selectedFile = null;
            uploadButton.disabled = true;
            fileInfo.classList.remove('show');
            return;
        }
        
        // Show file info
        const sizeInMB = (selectedFile.size / (1024 * 1024)).toFixed(2);
        const sizeInGB = (selectedFile.size / (1024 * 1024 * 1024)).toFixed(2);
        const displaySize = selectedFile.size > 1024 * 1024 * 1024 ? `${sizeInGB} GB` : `${sizeInMB} MB`;
        fileInfo.textContent = `✓ ${selectedFile.name} (${displaySize})`;
        fileInfo.classList.add('show');
        uploadButton.disabled = false;
        
        // Try to auto-populate metadata from Google Books API
        const bookTitle = selectedFile.name.replace('.zip', '');
        fetchBookMetadata(bookTitle);
    } else {
        selectedFile = null;
        uploadButton.disabled = true;
        fileInfo.classList.remove('show');
    }
}

async function fetchBookMetadata(bookTitle) {
    const statusEl = document.getElementById('apiLookupStatus');
    const authorInput = document.getElementById('authorName');
    const seriesNameInput = document.getElementById('uploadSeriesName');
    const seriesOrderInput = document.getElementById('uploadSeriesOrder');
    
    // Show loading status
    statusEl.textContent = '🔍 Looking up book information...';
    statusEl.style.display = 'block';
    statusEl.style.color = '#7f8c8d';
    
    try {
        // Clean up the title for better search results
        let searchQuery = bookTitle;
        
        // If format is "Author - Title", extract just the title for search
        if (bookTitle.includes(' - ')) {
            const parts = bookTitle.split(' - ');
            searchQuery = parts[1] || parts[0];
        }
        
        // Call Google Books API
        const response = await fetch(
            `https://www.googleapis.com/books/v1/volumes?q=${encodeURIComponent(searchQuery)}&maxResults=1`
        );
        
        if (!response.ok) {
            throw new Error('API request failed');
        }
        
        const data = await response.json();
        
        if (data.items && data.items.length > 0) {
            const book = data.items[0].volumeInfo;
            
            // Auto-fill author if available and field is empty
            if (book.authors && book.authors.length > 0 && !authorInput.value) {
                authorInput.value = book.authors[0];
            }
            
            // Check for series information in the title or description
            const title = book.title || '';
            const subtitle = book.subtitle || '';
            const fullTitle = subtitle ? `${title}: ${subtitle}` : title;
            
            // Try to extract series info from title
            // Common patterns: "Series Name, Book 1", "Series Name #1", "(Series Name Book 1)"
            const seriesPatterns = [
                /\(([^)]+?)\s+(?:Book|#)\s*(\d+)\)/i,  // (Series Name Book 1) or (Series Name #1)
                /([^,]+),\s+(?:Book|Volume|Vol\.?)\s*(\d+)/i,  // Series Name, Book 1
                /:?\s*(?:Book|Volume|Vol\.?)\s*(\d+)\s+of\s+(.+)/i,  // Book 1 of Series Name
                /([^#]+)\s+#(\d+)/,  // Series Name #1
            ];
            
            let seriesFound = false;
            for (const pattern of seriesPatterns) {
                const match = fullTitle.match(pattern);
                if (match) {
                    if (!seriesNameInput.value) {
                        seriesNameInput.value = match[1].trim();
                    }
                    if (!seriesOrderInput.value) {
                        seriesOrderInput.value = match[2];
                    }
                    seriesFound = true;
                    break;
                }
            }
            
            statusEl.textContent = seriesFound 
                ? '✓ Found book information and series details' 
                : '✓ Found book information (no series detected)';
            statusEl.style.color = '#27ae60';
        } else {
            statusEl.textContent = 'ℹ️ No book information found - you can fill in manually';
            statusEl.style.color = '#7f8c8d';
        }
    } catch (error) {
        console.error('Error fetching book metadata:', error);
        statusEl.textContent = 'ℹ️ Could not fetch book information - you can fill in manually';
        statusEl.style.color = '#7f8c8d';
    }
    
    // Hide status after 5 seconds
    setTimeout(() => {
        statusEl.style.display = 'none';
    }, 5000);
}

async function uploadBook() {
    // Check if user is admin
    if (!window.isUserAdmin) {
        showAlert('❌ Only administrators can upload books', 'error');
        return;
    }
    
    if (!selectedFile) {
        showAlert('❌ Please select a file', 'error');
        return;
    }
    
    const authorInput = document.getElementById('authorName');
    const author = authorInput.value.trim();
    const seriesNameInput = document.getElementById('uploadSeriesName');
    const seriesName = seriesNameInput.value.trim();
    const seriesOrderInput = document.getElementById('uploadSeriesOrder');
    const seriesOrder = seriesOrderInput.value.trim();
    const uploadButton = document.getElementById('uploadButton');
    const progressDiv = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    try {
        // Disable upload button
        uploadButton.disabled = true;
        uploadButton.textContent = 'Uploading...';
        
        // Step 1: Get presigned upload URL from backend
        progressText.textContent = 'Preparing upload...';
        progressDiv.style.display = 'block';
        progressFill.style.width = '10%';
        
        const token = localStorage.getItem('idToken');
        if (!token) {
            throw new Error('Not authenticated. Please log in.');
        }
        
        const uploadRequestBody = {
            filename: selectedFile.name,
            fileSize: selectedFile.size,
            author: author || undefined
        };
        
        // Upload endpoint is at /upload (not /books/upload)
        const uploadUrl = API_URL.replace('/books', '') + '/upload';
        const response = await fetch(uploadUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(uploadRequestBody)
        });
        
        if (response.status === 401 || response.status === 403) {
            const refreshed = await refreshAuthToken();
            if (refreshed) {
                return uploadBook(); // Retry with new token
            } else {
                throw new Error('Session expired. Please log in again.');
            }
        }
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        const uploadData = await response.json();
        progressFill.style.width = '30%';
        
        // Step 2: Upload file to S3 using presigned PUT URL with XMLHttpRequest for progress tracking
        progressText.textContent = 'Uploading to S3...';
        
        await new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            
            // Track upload progress
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const percentComplete = (e.loaded / e.total) * 60; // 30% to 90% range
                    progressFill.style.width = `${30 + percentComplete}%`;
                    
                    // Show upload size
                    const mbLoaded = (e.loaded / 1024 / 1024).toFixed(1);
                    const mbTotal = (e.total / 1024 / 1024).toFixed(1);
                    if (e.total > 1024 * 1024 * 1024) {
                        // Show in GB for large files
                        const gbLoaded = (e.loaded / 1024 / 1024 / 1024).toFixed(2);
                        const gbTotal = (e.total / 1024 / 1024 / 1024).toFixed(2);
                        progressText.textContent = `Uploading: ${gbLoaded} GB / ${gbTotal} GB`;
                    } else {
                        progressText.textContent = `Uploading: ${mbLoaded} MB / ${mbTotal} MB`;
                    }
                }
            });
            
            xhr.addEventListener('load', () => {
                if (xhr.status === 200) {
                    progressFill.style.width = '90%';
                    progressText.textContent = 'Processing...';
                    resolve();
                } else {
                    reject(new Error(`S3 upload failed: ${xhr.status} ${xhr.statusText}`));
                }
            });
            
            xhr.addEventListener('error', () => {
                reject(new Error('Network error during S3 upload'));
            });
            
            xhr.addEventListener('abort', () => {
                reject(new Error('Upload was aborted'));
            });
            
            xhr.addEventListener('timeout', () => {
                reject(new Error('Upload timed out'));
            });
            
            // Set a longer timeout for large files (30 minutes)
            xhr.timeout = 1800000;
            
            xhr.open('PUT', uploadData.uploadUrl);
            xhr.setRequestHeader('Content-Type', 'application/zip');
            xhr.send(selectedFile);
        });
        
        progressFill.style.width = '95%';
        progressText.textContent = 'Processing...';
        
        // Wait for S3 trigger to process and create DynamoDB record
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Step 3: Set metadata (author, series fields) if provided
        if (author || seriesName || seriesOrder) {
            try {
                // Extract book ID from filename (remove .zip extension)
                const bookId = selectedFile.name.replace('.zip', '');
                
                const metadataUrl = API_URL.replace('/books', '') + '/upload/metadata';
                
                // Build metadata payload
                const metadataPayload = { bookId };
                if (author) metadataPayload.author = author;
                if (seriesName) metadataPayload.series_name = seriesName;
                if (seriesOrder) metadataPayload.series_order = parseInt(seriesOrder, 10);
                
                // Retry logic in case S3 trigger hasn't finished yet
                let retries = 3;
                let success = false;
                
                while (retries > 0 && !success) {
                    const metadataResponse = await fetch(metadataUrl, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify(metadataPayload)
                    });
                    
                    if (metadataResponse.ok) {
                        console.log(`Successfully set metadata for ${bookId}`);
                        success = true;
                    } else if (metadataResponse.status === 404) {
                        // Record not found yet, S3 trigger still processing
                        console.log(`Book record not ready yet, retrying... (${retries} attempts left)`);
                        retries--;
                        if (retries > 0) {
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                    } else {
                        console.warn(`Failed to set metadata: ${metadataResponse.status}`);
                        break;
                    }
                }
                
                if (!success) {
                    console.warn('Failed to set metadata after retries');
                }
            } catch (metadataError) {
                // Don't fail the entire upload if metadata update fails
                console.warn('Failed to set metadata:', metadataError);
            }
        }
        
        progressFill.style.width = '100%';
        progressText.textContent = 'Upload complete!';
        
        showAlert(`✅ Successfully uploaded ${selectedFile.name}`, 'success');
        
        // Close modal after short delay
        setTimeout(() => {
            closeUploadModal();
            // Refresh the books list
            fetchBooks();
        }, 1500);
        
    } catch (error) {
        showAlert(`❌ Upload failed: ${error.message}`, 'error');
        console.error('Error uploading book:', error);
        uploadButton.disabled = false;
        uploadButton.textContent = 'Upload';
        progressDiv.style.display = 'none';
    }
}

