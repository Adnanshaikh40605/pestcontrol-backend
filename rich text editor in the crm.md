Please help me implement a professional, responsive, and robust Rich Text Editor component using Quill (`react-quill` and `quill`) in my React project. 

The editor must match these exact specifications and high-end design styling:

### 1. Installation Requirements
If they are not installed, please tell me to install these packages or do it for me:
- `react-quill` (version 2.x)
- `quill` (version 2.x)
- `styled-components` (or standard CSS if styled-components isn't used)

### 2. Core Features Required
1. **Interactive Styling & Overrides**: Standard Quill styles look basic. I want custom css/styled-components overrides that stylize the toolbar, dropdown picker options, heading hierarchy (H1, H2, H3, etc.), blockquotes, lists, active/hover buttons, and custom border/background color matching theme variables (`var(--bg)`, `var(--text)`, `var(--primary)` etc.).
2. **Smart Sticky Toolbar**: The toolbar should stick to the top of the viewport when scrolling down past the editor, but *only* while the editor container is in view. It should release when the editor goes out of view.
3. **Scroll & Jump Protection**: When pasting text or clicking toolbar items, prevent the browser from automatically jumping or scrolling away. Implement helper event listeners (`paste`, `click`, `mousedown`, `focusin`) to freeze scroll updates during these interactions.
4. **Custom Backend Image Upload**: Instead of inserting heavy Base64 images directly into the HTML, clicking the toolbar's image button must trigger a custom handler that:
   - Opens a local file selection dialog (`input[type="file"]` only accepting `image/*`).
   - Validates file type and size (5MB limit).
   - Dynamically uploads the image via a `POST` request to my server endpoint (e.g. `/api/upload/quill/`).
   - Includes authentication headers if needed (`Authorization: Bearer <token>`).
   - Inserts the uploaded image URL dynamically into the editor at the cursor position and repositions the cursor.

---

### 3. Component Code Blueprint
Please implement this component under `src/components/QuillEditor.jsx` matching this structure:

```jsx
import React, { useMemo, useRef, useEffect, useState } from 'react';
import ReactQuill from 'react-quill';
import 'react-quill/dist/quill.snow.css';
import styled from 'styled-components';

// 🎨 Custom Styled Component container to override default Quill Snow theme
const EditorContainer = styled.div`
  position: relative;
  overflow: visible;
  
  .ql-editor {
    min-height: 300px;
    font-size: 16px;
    line-height: 1.6;
    background-color: var(--bg, #ffffff) !important;
    color: var(--text, #1a202c) !important;
    padding: 16px !important;
  }
  
  .ql-toolbar {
    position: sticky;
    top: 0;
    z-index: 1001;
    background-color: var(--bg, #ffffff) !important;
    border: 1px solid var(--border, #e2e8f0) !important;
    border-radius: 8px 8px 0 0;
    transition: all 0.3s ease;
  }
  
  .ql-toolbar.toolbar-fixed {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 1001 !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1) !important;
    border-radius: 0 !important;
  }
  
  .ql-container {
    border: 1px solid var(--border, #e2e8f0) !important;
    border-top: none !important;
    border-radius: 0 0 8px 8px;
  }

  /* Custom styling for headers and blockquotes */
  .ql-editor h1 { font-size: 2.25rem; font-weight: 800; margin: 1.5rem 0 1rem 0; color: #1a202c; }
  .ql-editor h2 { font-size: 1.75rem; font-weight: 700; margin: 1.25rem 0 0.75rem 0; color: #2d3748; }
  .ql-editor h3 { font-size: 1.5rem; font-weight: 600; margin: 1rem 0 0.5rem 0; color: #4a5568; }
  
  .ql-editor blockquote {
    border-left: 4px solid var(--primary, #3182ce);
    background-color: var(--surface-light, #f7fafc);
    padding: 12px 16px;
    margin: 16px 0;
    font-style: italic;
  }
  
  .ql-editor img {
    max-width: 100%;
    height: auto;
    border-radius: 4px;
  }
`;

const QuillEditor = ({ value, onChange, placeholder = "Write your content here...", readOnly = false }) => {
  const quillRef = useRef(null);
  const editorContainerRef = useRef(null);
  const [isToolbarFixed, setIsToolbarFixed] = useState(false);

  // 1. Toolbar Scroll & Paste Prevention logic goes here
  useEffect(() => {
    let isPasting = false;
    let isToolbarAction = false;
    let pasteTimeout, toolbarActionTimeout;
    let savedScrollPosition = 0;
    let savedToolbarState = false;

    const handleScroll = () => {
      if (isPasting || isToolbarAction || !quillRef.current || !editorContainerRef.current) return;
      const editorContainer = editorContainerRef.current;
      const toolbar = editorContainer.querySelector('.ql-toolbar');
      if (!toolbar) return;

      const containerRect = editorContainer.getBoundingClientRect();
      const toolbarHeight = toolbar.offsetHeight || 50;
      const isEditorInView = containerRect.top <= 0 && containerRect.bottom > toolbarHeight;

      if (isEditorInView && !isToolbarFixed) {
        toolbar.classList.add('toolbar-fixed');
        setIsToolbarFixed(true);
      } else if (!isEditorInView && isToolbarFixed) {
        toolbar.classList.remove('toolbar-fixed');
        setIsToolbarFixed(false);
      }
    };

    const handlePasteStart = () => {
      isPasting = true;
      savedScrollPosition = window.scrollY;
      savedToolbarState = isToolbarFixed;
      clearTimeout(pasteTimeout);
      pasteTimeout = setTimeout(() => {
        isPasting = false;
        if (Math.abs(window.scrollY - savedScrollPosition) > 10) {
          window.scrollTo({ top: savedScrollPosition, behavior: 'instant' });
        }
      }, 2000);
    };

    const handleToolbarActionStart = () => {
      isToolbarAction = true;
      savedScrollPosition = window.scrollY;
      savedToolbarState = isToolbarFixed;
      clearTimeout(toolbarActionTimeout);
      toolbarActionTimeout = setTimeout(() => {
        isToolbarAction = false;
        if (Math.abs(window.scrollY - savedScrollPosition) > 5) {
          window.scrollTo({ top: savedScrollPosition, behavior: 'instant' });
        }
      }, 300);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    // Add paste and toolbar click preventions
    return () => {
      window.removeEventListener('scroll', handleScroll);
      clearTimeout(pasteTimeout);
      clearTimeout(toolbarActionTimeout);
    };
  }, [isToolbarFixed]);

  // 2. Custom Image Uploader Handler to your Backend
  const imageHandler = () => {
    const input = document.createElement('input');
    input.setAttribute('type', 'file');
    input.setAttribute('accept', 'image/*');
    input.click();

    input.onchange = async () => {
      const file = input.files[0];
      if (!file) return;

      if (file.size > 5 * 1024 * 1024) {
        alert('Image size should be less than 5MB');
        return;
      }

      try {
        const formData = new FormData();
        formData.append('image', file);

        const response = await fetch('/api/upload/quill/', {
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('accessToken')}`
          }
        });

        if (response.ok) {
          const data = await response.json();
          const quill = quillRef.current.getEditor();
          const range = quill.getSelection();
          quill.insertEmbed(range.index, 'image', data.url);
          quill.setSelection(range.index + 1);
        } else {
          throw new Error('Upload failed');
        }
      } catch (error) {
        console.error('Error uploading image:', error);
        alert('Failed to upload image.');
      }
    };
  };

  // 3. Modules configurations
  const modules = useMemo(() => ({
    toolbar: {
      container: [
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
        ['bold', 'italic', 'underline', 'strike'],
        [{ 'color': [] }, { 'background': [] }],
        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
        [{ 'indent': '-1' }, { 'indent': '+1' }],
        ['blockquote', 'code-block'],
        ['link', 'image', 'video'],
        [{ 'align': [] }],
        ['clean']
      ],
      handlers: {
        image: imageHandler
      }
    },
    clipboard: { matchVisual: false }
  }), []);

  const formats = [
    'header', 'bold', 'italic', 'underline', 'strike',
    'color', 'background', 'list', 'bullet', 'indent',
    'blockquote', 'code-block', 'link', 'image', 'video',
    'align', 'clean'
  ];

  return (
    <EditorContainer ref={editorContainerRef}>
      <ReactQuill
        ref={quillRef}
        theme="snow"
        value={value || ''}
        onChange={onChange}
        modules={modules}
        formats={formats}
        placeholder={placeholder}
        readOnly={readOnly}
      />
    </EditorContainer>
  );
};

export default QuillEditor;
