import { useEffect, useState } from "react";
import {
  getEmployerRecentCategorySelections,
  getWorkerRecentCategorySelections,
  listCategoryGroups,
  listGroupRoles,
  verifyCustomRole,
  type CategoryGroup,
  type CategoryRole,
  type CategorySelection,
  type CustomRoleVerifyResult,
} from "../api/client";
import { useCategoryGlobalSearch } from "../hooks/useCategoryGlobalSearch";
import { filterRoles } from "../utils/categorySearch";
import { triggerHaptic } from "../lib/telegram";

type CategoryPickerContext = "employer" | "worker";

type CategoryPickerProps = {
  initData: string;
  context: CategoryPickerContext;
  value: CategorySelection | null;
  onChange: (value: CategorySelection | null) => void;
  disabled?: boolean;
  error?: string | null;
  allowCustomRole?: boolean;
  customVerifyResult?: CustomRoleVerifyResult | null;
  onCustomVerifyResultChange?: (result: CustomRoleVerifyResult | null) => void;
  label?: string;
};

type PickerStep = "group" | "role" | "custom";

function selectionFromRecent(item: CategorySelection): CategorySelection {
  return {
    group_id: item.group_id,
    group_slug: item.group_slug,
    group_name_ru: item.group_name_ru,
    role_id: item.role_id,
    role_slug: item.role_slug,
    role_name_ru: item.role_name_ru,
    legacy_category_id: item.legacy_category_id,
    is_custom: false,
    custom_title: null,
  };
}

function selectionFromGroupRole(group: CategoryGroup, role: CategoryRole): CategorySelection {
  return {
    group_id: group.id,
    group_slug: group.slug,
    group_name_ru: group.name_ru,
    role_id: role.id,
    role_slug: role.slug,
    role_name_ru: role.name_ru,
    legacy_category_id: role.legacy_category_id,
    is_custom: false,
    custom_title: null,
  };
}

function selectionFromSearchResult(
  result: { group_slug: string; group_name_ru: string; role_id: number; role_slug?: string; name_ru: string; legacy_category_id: number | null },
  groupId: number,
): CategorySelection {
  return {
    group_id: groupId,
    group_slug: result.group_slug,
    group_name_ru: result.group_name_ru,
    role_id: result.role_id,
    role_slug: result.role_slug ?? "",
    role_name_ru: result.name_ru,
    legacy_category_id: result.legacy_category_id,
    is_custom: false,
    custom_title: null,
  };
}

export function legacyCategoryId(selection: CategorySelection): number | null {
  if (selection.legacy_category_id === null) {
    return selection.role_id > 0 ? selection.role_id : null;
  }
  return selection.legacy_category_id;
}

function isSelectableRole(role: CategoryRole): boolean {
  return role.id > 0;
}

function isSelectableSearchResult(result: { role_id: number }): boolean {
  return result.role_id > 0;
}

function formatSelectionLabel(selection: CategorySelection): string {
  if (selection.is_custom && selection.custom_title) {
    return `${selection.group_name_ru} · ${selection.custom_title}`;
  }
  return `${selection.group_name_ru} · ${selection.role_name_ru}`;
}

export function isCategorySelectionValid(
  selection: CategorySelection | null,
  customVerifyResult?: CustomRoleVerifyResult | null,
): boolean {
  if (!selection) {
    return false;
  }
  if (selection.is_custom) {
    return customVerifyResult?.status === "approved";
  }
  return legacyCategoryId(selection) !== null;
}

export function categorySelectionToFormFields(selection: CategorySelection | null): {
  category_id: string;
  title: string;
} {
  if (!selection) {
    return { category_id: "", title: "" };
  }
  const categoryId = legacyCategoryId(selection);
  const title =
    selection.is_custom && selection.custom_title ? selection.custom_title : selection.role_name_ru;
  return { category_id: categoryId === null ? "" : String(categoryId), title };
}

function CustomRoleVerifyCard({
  result,
  onApplySuggestion,
  onAcceptMapped,
}: {
  result: CustomRoleVerifyResult;
  onApplySuggestion: () => void;
  onAcceptMapped: () => void;
}) {
  const cardClass = `verify-card verify-card--${result.status}`;

  if (result.status === "approved") {
    return (
      <div className={cardClass}>
        <strong>Одобрено</strong>
        <p>{result.reason}</p>
        <p className="hint">Можно публиковать заявку с названием «{result.proposed_title}»</p>
      </div>
    );
  }

  if (result.status === "map_to_existing") {
    return (
      <div className={cardClass}>
        <strong>Есть стандартная должность</strong>
        <p>{result.reason}</p>
        {result.category_name_ru ? (
          <button type="button" className="btn secondary" onClick={onAcceptMapped}>
            Выбрать «{result.category_name_ru}»
          </button>
        ) : null}
      </div>
    );
  }

  if (result.status === "revise") {
    return (
      <div className={cardClass}>
        <strong>Уточните название</strong>
        <p>{result.reason}</p>
        {result.suggested_title ? (
          <button type="button" className="btn secondary" onClick={onApplySuggestion}>
            Использовать «{result.suggested_title}»
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div className={cardClass}>
      <strong>Отклонено</strong>
      <p>{result.reason}</p>
      <p className="hint">Измените название или выберите стандартную должность.</p>
    </div>
  );
}

export function CategoryPicker({
  initData,
  context,
  value,
  onChange,
  disabled = false,
  error = null,
  allowCustomRole = false,
  customVerifyResult = null,
  onCustomVerifyResultChange,
  label = "Категория",
}: CategoryPickerProps) {
  const [step, setStep] = useState<PickerStep>("group");
  const [groups, setGroups] = useState<CategoryGroup[]>([]);
  const [groupsError, setGroupsError] = useState<string | null>(null);
  const [groupsLoading, setGroupsLoading] = useState(true);
  const [recentSelections, setRecentSelections] = useState<CategorySelection[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<CategoryGroup | null>(null);
  const [groupRoles, setGroupRoles] = useState<CategoryRole[]>([]);
  const [rolesLoading, setRolesLoading] = useState(false);
  const [rolesError, setRolesError] = useState<string | null>(null);
  const [customTitle, setCustomTitle] = useState("");
  const [customVerifying, setCustomVerifying] = useState(false);
  const [customError, setCustomError] = useState<string | null>(null);

  const {
    categoryQuery,
    setCategoryQuery,
    categoryResults,
    categoryLoading,
    handleCategoryFocus,
    handleCategoryBlur,
    resetCategorySearch,
  } = useCategoryGlobalSearch({ enabled: step === "group" && !disabled });

  const showSearchResults = categoryQuery.trim().length >= 1;

  useEffect(() => {
    if (step !== "role" || !selectedGroup || disabled) {
      setGroupRoles([]);
      setRolesLoading(false);
      setRolesError(null);
      return;
    }

    let cancelled = false;
    setRolesLoading(true);
    setRolesError(null);

    void listGroupRoles(selectedGroup.slug)
      .then((roles) => {
        if (!cancelled) {
          setGroupRoles(filterRoles(roles, ""));
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setGroupRoles([]);
          setRolesError(err instanceof Error ? err.message : "Не удалось загрузить должности");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setRolesLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [disabled, selectedGroup, step]);

  useEffect(() => {
    let cancelled = false;
    setGroupsLoading(true);

    void listCategoryGroups()
      .then((data) => {
        if (!cancelled) {
          setGroups(data);
          setGroupsError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setGroupsError(err instanceof Error ? err.message : "Не удалось загрузить группы");
        }
      })
      .finally(() => {
        if (!cancelled) {
          setGroupsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const loadRecent =
      context === "employer"
        ? getEmployerRecentCategorySelections(initData)
        : getWorkerRecentCategorySelections(initData);

    void loadRecent
      .then((response) => {
        if (!cancelled) {
          setRecentSelections(response.items);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRecentSelections([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [context, initData]);

  function clearRoles() {
    setGroupRoles([]);
    setRolesLoading(false);
    setRolesError(null);
  }

  function resetPicker() {
    onChange(null);
    onCustomVerifyResultChange?.(null);
    setSelectedGroup(null);
    setCustomTitle("");
    setCustomError(null);
    resetCategorySearch();
    clearRoles();
    setStep("group");
  }

  function selectGroup(group: CategoryGroup) {
    triggerHaptic("light");
    setSelectedGroup(group);
    clearRoles();
    setStep("role");
  }

  function selectRole(role: CategoryRole) {
    if (!selectedGroup || !isSelectableRole(role)) {
      return;
    }
    triggerHaptic("light");
    onChange(selectionFromGroupRole(selectedGroup, role));
    onCustomVerifyResultChange?.(null);
    setCustomTitle("");
    setCustomError(null);
    clearRoles();
    setStep("group");
  }

  function selectRecent(item: CategorySelection) {
    triggerHaptic("light");
    onChange(selectionFromRecent(item));
    onCustomVerifyResultChange?.(null);
    setCustomTitle("");
    setCustomError(null);
    setSelectedGroup(groups.find((g) => g.id === item.group_id) ?? null);
    resetCategorySearch();
    clearRoles();
    setStep("group");
  }

  function selectSearchResult(result: {
    group_slug: string;
    group_name_ru: string;
    role_id: number;
    role_slug?: string;
    name_ru: string;
    legacy_category_id: number | null;
  }) {
    if (!isSelectableSearchResult(result)) {
      return;
    }
    const group = groups.find((g) => g.slug === result.group_slug);
    triggerHaptic("light");
    onChange(selectionFromSearchResult(result, group?.id ?? 0));
    onCustomVerifyResultChange?.(null);
    setCustomTitle("");
    setCustomError(null);
    setSelectedGroup(group ?? null);
    resetCategorySearch();
    clearRoles();
    setStep("group");
  }

  function backToGroups() {
    setSelectedGroup(null);
    resetCategorySearch();
    clearRoles();
    setStep("group");
  }

  function startCustomRole() {
    if (!selectedGroup) {
      return;
    }
    triggerHaptic("light");
    onChange(null);
    onCustomVerifyResultChange?.(null);
    setCustomTitle("");
    setCustomError(null);
    setStep("custom");
  }

  function backToRoles() {
    onCustomVerifyResultChange?.(null);
    setCustomTitle("");
    setCustomError(null);
    setStep("role");
  }

  async function verifyCustomTitle() {
    if (!selectedGroup || !customTitle.trim()) {
      setCustomError("Укажите название должности");
      return;
    }

    setCustomVerifying(true);
    setCustomError(null);
    onCustomVerifyResultChange?.(null);

    try {
      const result = await verifyCustomRole(initData, {
        group_id: selectedGroup.id,
        group_slug: selectedGroup.slug,
        proposed_title: customTitle.trim(),
      });
      onCustomVerifyResultChange?.(result);

      if (result.status === "approved") {
        onChange({
          group_id: selectedGroup.id,
          group_slug: selectedGroup.slug,
          group_name_ru: selectedGroup.name_ru,
          role_id: 0,
          role_slug: result.role_slug ?? "custom",
          role_name_ru: result.proposed_title,
          legacy_category_id: result.category_id ?? null,
          is_custom: true,
          custom_title: result.proposed_title,
        });
      } else if (result.status === "map_to_existing" && result.category_id) {
        onChange({
          group_id: selectedGroup.id,
          group_slug: selectedGroup.slug,
          group_name_ru: selectedGroup.name_ru,
          role_id: 0,
          role_slug: result.role_slug ?? result.category_slug ?? "mapped",
          role_name_ru: result.category_name_ru ?? result.proposed_title,
          legacy_category_id: result.category_id,
          is_custom: false,
          custom_title: null,
        });
      }
    } catch (err) {
      setCustomError(err instanceof Error ? err.message : "Не удалось проверить должность");
    } finally {
      setCustomVerifying(false);
    }
  }

  function applySuggestion() {
    if (customVerifyResult?.suggested_title) {
      setCustomTitle(customVerifyResult.suggested_title);
      onCustomVerifyResultChange?.(null);
    }
  }

  function acceptMappedRole() {
    if (
      !customVerifyResult ||
      customVerifyResult.status !== "map_to_existing" ||
      !selectedGroup ||
      !customVerifyResult.category_id
    ) {
      return;
    }
    triggerHaptic("light");
    onChange({
      group_id: selectedGroup.id,
      group_slug: selectedGroup.slug,
      group_name_ru: selectedGroup.name_ru,
      role_id: 0,
      role_slug: customVerifyResult.role_slug ?? customVerifyResult.category_slug ?? "mapped",
      role_name_ru: customVerifyResult.category_name_ru ?? customVerifyResult.proposed_title,
      legacy_category_id: customVerifyResult.category_id,
      is_custom: false,
      custom_title: null,
    });
    onCustomVerifyResultChange?.(null);
    setCustomTitle("");
    setStep("group");
  }

  if (value && step === "group") {
    return (
      <div className="form-field category-picker">
        <span>{label}</span>
        <div className="category-selected">
          <span>{formatSelectionLabel(value)}</span>
          <button type="button" className="link-btn" disabled={disabled} onClick={resetPicker}>
            Изменить
          </button>
        </div>
        {error ? <em className="field-error">{error}</em> : null}
      </div>
    );
  }

  return (
    <div className="form-field category-picker">
      <span>{label}</span>
      {groupsError ? <p className="error">{groupsError}</p> : null}
      {groupsLoading ? <p className="hint">Загрузка групп…</p> : null}

      {step === "group" ? (
        <>
          <input
            type="search"
            value={categoryQuery}
            placeholder="Поиск должности…"
            disabled={disabled || groupsLoading}
            onFocus={handleCategoryFocus}
            onBlur={handleCategoryBlur}
            onChange={(e) => setCategoryQuery(e.target.value)}
          />
          {showSearchResults ? (
            <>
              {categoryLoading ? <p className="hint">Поиск…</p> : null}
              {categoryResults.length > 0 ? (
                <ul className="metro-results category-role-results">
                  {categoryResults.map((item) => (
                    <li key={`${item.group_slug}-${item.role_id}`}>
                      <button
                        type="button"
                        className="metro-option"
                        disabled={disabled || !isSelectableSearchResult(item)}
                        onClick={() => selectSearchResult(item)}
                      >
                        {item.group_name_ru} · {item.name_ru}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : categoryLoading ? null : (
                <p className="hint">Ничего не найдено</p>
              )}
            </>
          ) : (
            <>
              {recentSelections.length > 0 ? (
                <div className="category-recent">
                  <p className="hint">Недавние</p>
                  <div className="filter-chips">
                    {recentSelections.map((item) => (
                      <button
                        key={`${item.group_id}-${item.role_id}`}
                        type="button"
                        className="chip"
                        disabled={disabled}
                        onClick={() => selectRecent(item)}
                      >
                        {item.role_name_ru}
                      </button>
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="category-group-grid">
                {groups.map((group) => (
                  <button
                    key={group.id}
                    type="button"
                    className="category-group-card"
                    disabled={disabled || groupsLoading}
                    onClick={() => selectGroup(group)}
                  >
                    <span className="category-group-card__title">{group.name_ru}</span>
                    <span className="category-group-card__count hint">{group.roles_count} ролей</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </>
      ) : null}

      {step === "role" && selectedGroup ? (
        <div className="category-role-step">
          <button type="button" className="link-btn back-link" disabled={disabled} onClick={backToGroups}>
            ← {selectedGroup.name_ru}
          </button>
          {rolesLoading ? <p className="hint">Загрузка должностей…</p> : null}
          {rolesError ? <p className="error">{rolesError}</p> : null}
          {groupRoles.length > 0 ? (
            <ul className="metro-results category-role-results">
              {groupRoles.map((role) => (
                <li key={role.id}>
                  <button
                    type="button"
                    className="metro-option"
                    disabled={disabled || !isSelectableRole(role)}
                    onClick={() => selectRole(role)}
                  >
                    {role.name_ru}
                  </button>
                </li>
              ))}
            </ul>
          ) : !rolesLoading && !rolesError ? (
            <p className="hint">Нет доступных должностей в этой группе.</p>
          ) : null}
          {allowCustomRole ? (
            <button
              type="button"
              className="btn secondary category-custom-btn"
              disabled={disabled}
              onClick={startCustomRole}
            >
              Своя должность
            </button>
          ) : null}
        </div>
      ) : null}

      {step === "custom" && selectedGroup && allowCustomRole ? (
        <div className="category-custom-step">
          <button type="button" className="link-btn back-link" disabled={disabled} onClick={backToRoles}>
            ← К списку должностей
          </button>
          <p className="hint">Группа: {selectedGroup.name_ru}</p>
          <label className="form-field compact">
            <span>Название должности</span>
            <input
              type="text"
              maxLength={200}
              value={customTitle}
              disabled={disabled || customVerifying}
              onChange={(e) => {
                setCustomTitle(e.target.value);
                setCustomError(null);
                onCustomVerifyResultChange?.(null);
              }}
              onBlur={() => {
                if (customTitle.trim()) {
                  void verifyCustomTitle();
                }
              }}
            />
          </label>
          <button
            type="button"
            className="btn secondary"
            disabled={disabled || customVerifying || !customTitle.trim()}
            onClick={() => void verifyCustomTitle()}
          >
            {customVerifying ? "Проверка…" : "Проверить"}
          </button>
          {customError ? <em className="field-error">{customError}</em> : null}
          {customVerifyResult ? (
            <CustomRoleVerifyCard
              result={customVerifyResult}
              onApplySuggestion={applySuggestion}
              onAcceptMapped={acceptMappedRole}
            />
          ) : null}
        </div>
      ) : null}

      {error ? <em className="field-error">{error}</em> : null}
    </div>
  );
}
