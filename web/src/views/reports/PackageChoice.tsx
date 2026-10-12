import { useId } from "react";

import { PACKAGE_OPTIONS, type PackageType } from "./package-options";

/** The two-option package control (#146); see package-options.ts. */
export function PackageChoice({
  value,
  onChange,
  disabled = false,
}: {
  value: PackageType;
  onChange: (next: PackageType) => void;
  disabled?: boolean;
}) {
  const group = useId();
  return (
    <fieldset className="package-choice" disabled={disabled}>
      <legend>Package</legend>
      {PACKAGE_OPTIONS.map((option) => (
        <label key={option.value} className={value === option.value ? "selected" : undefined}>
          <input
            type="radio"
            name={group}
            value={option.value}
            checked={value === option.value}
            onChange={() => onChange(option.value)}
          />
          <span>
            <strong>{option.label}</strong>
            <small>{option.sentence}</small>
          </span>
        </label>
      ))}
    </fieldset>
  );
}
