import { createApp } from 'vue'
import App from './App.vue'
import './styles.css'

// Inside the talk's slide the lab always uses the light theme of the deck and
// hands slide navigation keys back to the presentation.
if (new URLSearchParams(location.search).get('embed') === '1') {
  document.documentElement.dataset.theme = 'light'
  if (window.parent !== window) {
    window.addEventListener('keydown', (event) => {
      if (['PageDown', 'PageUp', 'Escape'].includes(event.key)) {
        event.preventDefault()
        window.parent.postMessage({ type: 'lab:key', key: event.key }, '*')
      }
    })
  }
}

createApp(App).mount('#app')
