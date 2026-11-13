import { createRoot } from 'react-dom/client'
import WardenPage from '../src/App'

document.body.style.margin = '0'
document.body.style.background = '#000'
createRoot(document.getElementById('root')!).render(<WardenPage />)
