import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select'
import { WORKFLOWS } from '../types'

interface WorkflowSelectorProps {
  value: string
  onChange: (value: string) => void
}

export function WorkflowSelector({ value, onChange }: WorkflowSelectorProps) {
  return (
    <div className="relative">
      <Select value={value} onValueChange={onChange}>
        <SelectTrigger className="w-full" aria-label="Sélectionner un workflow">
          <SelectValue placeholder="Choisir un workflow" />
        </SelectTrigger>
        <SelectContent>
          {WORKFLOWS.map((wf) => (
            <SelectItem key={wf.value} value={wf.value}>
              <span className="font-medium">{wf.label}</span>
              <span className="ml-2 text-xs text-muted-foreground hidden sm:inline">
                — {wf.description}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {/* Native select for Playwright automation — visuellement masqué */}
      <select
        data-testid="workflow-selector"
        className="sr-only"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        aria-hidden="true"
        tabIndex={-1}
      >
        {WORKFLOWS.map((wf) => (
          <option key={wf.value} value={wf.value}>{wf.label}</option>
        ))}
      </select>
    </div>
  )
}
