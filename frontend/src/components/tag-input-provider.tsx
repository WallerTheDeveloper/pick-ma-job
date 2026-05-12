/**
 * TagInputProvider — shared DndContext for cross-field tag drag-and-drop.
 *
 * Wrap TagInput instances with this provider to enable dragging tags
 * between different fields (e.g. from "Primary Skills" to "Secondary Skills").
 * Without this provider, TagInput still supports internal reorder via its
 * own local DndContext.
 */

import {
  createContext,
  useContext,
  useCallback,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  DndContext,
  closestCenter,
  type DragStartEvent,
  type DragEndEvent,
} from "@dnd-kit/core";
import { arrayMove } from "@dnd-kit/sortable";
import { toast } from "sonner";

// ── Types ────────────────────────────────────────────────────────────────────

export interface FieldRegistration {
  value: string[];
  onChange: (tags: string[]) => void;
  fieldLabel: string;
}

interface TagInputContextValue {
  /** Register a field so the provider can manage it for cross-field DnD. */
  registerField: (key: string, reg: FieldRegistration) => void;
  /** Unregister a field when its TagInput unmounts. */
  unregisterField: (key: string) => void;
  /** The id of the tag currently being dragged (null when idle). */
  activeId: string | null;
}

const TagInputContext = createContext<TagInputContextValue | null>(null);

/** Hook to access the tag-input provider context. Returns null if no provider. */
export function useTagInputContext(): TagInputContextValue | null {
  return useContext(TagInputContext);
}

// ── Helper ────────────────────────────────────────────────────────────────────

/** Parse a sortable tag id into [fieldKey, tagValue]. */
export function parseTagId(id: string): [string, string] {
  const sep = id.indexOf("::");
  if (sep === -1) return ["", id];
  return [id.slice(0, sep), id.slice(sep + 2)];
}

/** Build a sortable tag id from fieldKey and tagValue. */
export function buildTagId(fieldKey: string, tagValue: string): string {
  return `${fieldKey}::${tagValue}`;
}

/** Build a droppable container id for a field. */
export function buildContainerId(fieldKey: string): string {
  return `container::${fieldKey}`;
}

// ── Provider ──────────────────────────────────────────────────────────────────

interface TagInputProviderProps {
  children: ReactNode;
}

export function TagInputProvider({ children }: TagInputProviderProps) {
  const fieldsRef = useRef<Map<string, FieldRegistration>>(new Map());
  const [activeId, setActiveId] = useState<string | null>(null);

  const registerField = useCallback(
    (key: string, reg: FieldRegistration) => {
      fieldsRef.current.set(key, reg);
    },
    [],
  );

  const unregisterField = useCallback((key: string) => {
    fieldsRef.current.delete(key);
  }, []);

  // ── DnD handlers ────────────────────────────────────────────────────────

  function handleDragStart(event: DragStartEvent) {
    setActiveId(event.active.id as string);
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveId(null);
    const { active, over } = event;
    if (!over) return;

    const [sourceField, tagValue] = parseTagId(active.id as string);
    const overId = over.id as string;

    // Determine whether over is a tag (sortable) or a container (droppable)
    let targetField: string;
    let insertBeforeTag: string | null = null;

    if (overId.startsWith("container::")) {
      // Dropped on an empty area of a container
      targetField = overId.replace("container::", "");
    } else {
      // Dropped on a specific tag — parse both field and tag
      [targetField, insertBeforeTag] = parseTagId(overId);
    }

    const sourceReg = fieldsRef.current.get(sourceField);
    if (!sourceReg) return;

    if (sourceField === targetField) {
      // ── Same field: reorder ────────────────────────────────────────────
      const overIndex = insertBeforeTag
        ? sourceReg.value.indexOf(insertBeforeTag)
        : sourceReg.value.length - 1;
      if (overIndex === -1) return;
      const activeIndex = sourceReg.value.indexOf(tagValue);
      if (activeIndex === -1) return;
      if (activeIndex === overIndex) return;
      sourceReg.onChange(arrayMove(sourceReg.value, activeIndex, overIndex));
    } else {
      // ── Cross-field: move tag ──────────────────────────────────────────
      const targetReg = fieldsRef.current.get(targetField);
      if (!targetReg) return;

      // Check exact duplicate in target field
      if (targetReg.value.includes(tagValue)) {
        toast.error(`"${tagValue}" already exists in ${targetReg.fieldLabel}`);
        return;
      }

      // Check case-insensitive duplicate in target field
      const existingMatch = targetReg.value.find(
        (v) => v.toLowerCase() === tagValue.toLowerCase(),
      );
      if (existingMatch) {
        toast.error(
          `"${existingMatch}" already exists in ${targetReg.fieldLabel}`,
        );
        return;
      }

      // Remove from source
      sourceReg.onChange(sourceReg.value.filter((t) => t !== tagValue));

      // Add to target at the correct position
      if (insertBeforeTag) {
        const targetIndex = targetReg.value.indexOf(insertBeforeTag);
        if (targetIndex !== -1) {
          const newValue = [...targetReg.value];
          newValue.splice(targetIndex, 0, tagValue);
          targetReg.onChange(newValue);
        } else {
          targetReg.onChange([...targetReg.value, tagValue]);
        }
      } else {
        targetReg.onChange([...targetReg.value, tagValue]);
      }
    }
  }

  const contextValue: TagInputContextValue = {
    registerField,
    unregisterField,
    activeId,
  };

  return (
    <TagInputContext.Provider value={contextValue}>
      <DndContext
        collisionDetection={closestCenter}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        {children}
      </DndContext>
    </TagInputContext.Provider>
  );
}