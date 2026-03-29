import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './App.css'
import { WorkbenchLayout } from './layout/WorkbenchLayout'
import { ScenarioBuilder } from './pages/ScenarioBuilder'
import { RunWorkspace } from './pages/RunWorkspace'
import { ValidationWorkspace } from './pages/ValidationWorkspace'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<WorkbenchLayout />}>
          <Route path="/" element={<ScenarioBuilder />} />
          <Route path="/validation" element={<ValidationWorkspace />} />
        </Route>
        <Route path="/runs/:runId/*" element={<RunWorkspace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
