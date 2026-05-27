# T10 - Drag & Drop Reorderable Tags

## Priority
Low

## Status
.Done

## Description
Make all TagInput instances support drag-and-drop reordering of tags. The order the user arranges tags in is the order saved to the backend. This requires integrating `@dnd-kit/core` and `@dnd-kit/sortable` into the TagInput component.

## Context
- `frontend/src/components/tag-input.tsx` — the current TagInput component. Tags are rendered as `<span>` elements with a remove button. They cannot be reordered.
- The order of skills in `primary_skills`, `secondary_skills`, etc. matters — it's the order sent to the backend and used in evaluation prompts.
- The project uses `npm` as its package manager (based on `frontend/package.json`).
- The existing UI uses shadcn/ui components (Badge, Button, etc.) and Tailwind CSS.

## Acceptance Criteria
- [ ] `@dnd-kit/core`, `@dnd-kit/sortable`, and `@dnd-kit/utilities` are installed as dependencies
- [ ] Tags can be reordered by dragging on desktop (mouse) and mobile (touch)
- [ ] Dragged tag shows visual feedback (elevation, opacity change)
- [ ] Drop indicator shows where the tag will be placed
- [ ] Dragging is contained within the tag container (using `restrictToParentElement` modifier)
- [ ] The remove (×) button on tags still works during drag operations
- [ ] The input field stays at the end of the tag list and remains functional
- [ ] `onChange` is called with the new array order when a tag is dropped
- [ ] Touch devices work correctly (add `touch-action: none` CSS)

## Implementation Notes

### 1. Install dependencies

```bash
cd frontend && npm install @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities @dnd-kit/modifiers
```

### 2. Rewrite `TagInput` component (`frontend/src/components/tag-input.tsx`)

The component needs significant rework to support sortable items. Key changes:

```tsx
import { DndContext, closestCenter, type DragEndEvent } from "@dnd-kit/core";
import { SortableContext, useSortable, horizontalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { restrictToParentElement } from "@dnd-kit/modifiers";

interface TagInputProps {
  value: string[];
  onChange: (tags: string[]) => void;
  placeholder?: string;
  className?: string;
  fieldName?: string;
  onDuplicateConfirm?: (existingSkill: string, newSkill: string, fieldName: string) => Promise<boolean>;
  onBeforeAdd?: (tag: string) => boolean | Promise<boolean>;
}

function SortableTag({ tag, onRemove }: { tag: string; onRemove: () => void }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: tag });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
    zIndex: isDragging ? 10 : 0,
  };

  return (
    <span
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="inline-flex items-center gap-0.5 rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground cursor-grab active:cursor-grabbing"
    >
      {tag}
      <button
        type="button"
        aria-label={`Remove ${tag}`}
        onClick={(e) => { e.stopPropagation(); onRemove(); }}
        className="ml-0.5 rounded-full p-0.5 hover:bg-muted-foreground/20 focus:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      >
        ×
      </button>
    </span>
  );
}

export function TagInput({ value, onChange, placeholder, className, fieldName, onDuplicateConfirm, onBeforeAdd }: TagInputProps) {
  const [inputValue, setInputValue] = useState("");

  // ... commit() function with onBeforeAdd and onDuplicateConfirm (from T08/T09)

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = value.indexOf(active.id as string);
    const newIndex = value.indexOf(over.id as string);
    if (oldIndex === -1 || newIndex === -1) return;

    const newValue = arrayMove(value, oldIndex, newIndex);
    onChange(newValue);
  }

  function removeTag(index: number) {
    onChange(value.filter((_, i) => i !== index));
  }

  return (
    <DndContext
      collisionDetection={closestCenter}
      modifiers={[restrictToParentElement]}
      onDragEnd={handleDragEnd}
    >
      <div
        className={cn(
          "flex flex-wrap gap-1.5 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 min-h-10 cursor-text",
          className,
        )}
        style={{ touchAction: "none" }}
        onClick={(e) => {
          const input = (e.currentTarget as HTMLDivElement).querySelector("input");
          input?.focus();
        }}
      >
        <SortableContext items={value} strategy={horizontalListSortingStrategy}>
          {value.map((tag, i) => (
            <SortableTag
              key={tag}
              tag={tag}
              onRemove={() => removeTag(i)}
            />
          ))}
        </SortableContext>
        <input
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          // ... commit on blur etc.
          placeholder={value.length === 0 ? placeholder : undefined}
          className="flex-1 min-w-24 bg-transparent outline-none placeholder:text-muted-foreground"
        />
      </div>
    </DndContext>
  );
}
```

### 3. Import `arrayMove`

Import `arrayMove` from `@dnd-kit/sortable` (or use a simple splice-based implementation).

### 4. Key considerations

- The `key` prop on `SortableTag` must be stable (use `tag` string, not index). This means duplicate tags are not allowed — which is already enforced by T08/T09.
- `touch-action: none` on the container div prevents scrolling conflicts on mobile.
- The input should NOT be a sortable item — it always stays at the end.
- The `restrictToParentElement` modifier keeps drag within the tag container bounds.
- The remove button's `e.stopPropagation()` prevents the click from triggering a drag.

## Dependencies
- T08 and T09 (duplicate skill detection) — these should be implemented first since the TagInput component will be significantly rewritten

## Files to Modify/Create
- `frontend/package.json` (modify — add dnd-kit dependencies)
- `frontend/src/components/tag-input.tsx` (rewrite — add DndContext, SortableContext, useSortable)

## Tests
- Drag a tag from position 1 to position 3 → tag order updates, `onChange` called with new order
- Remove button still works on sortable tags
- Add a new tag via input → appears at end, not at a random position
- Touch drag works on mobile viewport
- Dragging a tag outside the container does not move it (restricted to parent)
- Works for all TagInput instances across the app