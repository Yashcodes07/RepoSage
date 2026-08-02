import LandingPage from './pages/LandingPage';

// Single-page site now — the chat app is an embedded, scroll-to
// section on this same page (see LandingPage's #chat section) rather
// than a separate route, so there's no more navigation-away moment
// between "the pitch" and "the actual tool".
function App() {
  return <LandingPage />;
}

export default App;