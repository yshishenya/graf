# Data Model: Нижний toggle native панели

No persistent data model.

| Presentation element | Owner | Constraint |
|---|---|---|
| `inspectorExpanded` | existing SwiftUI state | unchanged |
| `InspectorDisclosureButton` | existing view | one instance per visible mode |
| expanded footer | `inspector` layout | non-scrolling, trailing, bottom |
| compact footer | `compactInspector` layout | existing bottom position |
