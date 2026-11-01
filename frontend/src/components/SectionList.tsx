import {
  DndContext,
  type DragEndEvent,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { ReportSection } from "../data/templates";

interface SectionRowProps {
  section: ReportSection;
  active: boolean;
  onSelect: (id: string) => void;
}

function SectionRow({ section, active, onSelect }: SectionRowProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: section.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <li
      ref={setNodeRef}
      style={style}
      className={`group flex items-center gap-2 rounded-sm border px-2.5 py-2 text-sm ${
        active
          ? "border-slate-line bg-paper-raised text-ink"
          : "border-transparent text-ink/70 hover:border-slate-line/40 hover:bg-paper-raised/60"
      } ${isDragging ? "opacity-60" : ""}`}
    >
      <button
        type="button"
        aria-label={`${section.title} bölümünü sürükle`}
        className="cursor-grab touch-none text-slate-muted hover:text-ink"
        {...attributes}
        {...listeners}
      >
        ⠿
      </button>
      <button
        type="button"
        onClick={() => onSelect(section.id)}
        className="flex-1 truncate text-left font-sans"
      >
        {section.title}
      </button>
    </li>
  );
}

interface SectionListProps {
  sections: ReportSection[];
  activeId: string;
  onSelect: (id: string) => void;
  onReorder: (sections: ReportSection[]) => void;
}

export function SectionList({ sections, activeId, onSelect, onReorder }: SectionListProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = sections.findIndex((s) => s.id === active.id);
    const newIndex = sections.findIndex((s) => s.id === over.id);
    onReorder(arrayMove(sections, oldIndex, newIndex));
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <SortableContext items={sections.map((s) => s.id)} strategy={verticalListSortingStrategy}>
        <ul className="flex flex-col gap-1">
          {sections.map((section) => (
            <SectionRow
              key={section.id}
              section={section}
              active={section.id === activeId}
              onSelect={onSelect}
            />
          ))}
        </ul>
      </SortableContext>
    </DndContext>
  );
}
