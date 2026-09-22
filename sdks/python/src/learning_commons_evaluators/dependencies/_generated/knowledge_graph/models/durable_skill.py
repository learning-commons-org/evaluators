from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.grade_level_enum import GradeLevelENUM
from ..models.jurisdiction_enum import JurisdictionENUM
from ..models.language_enum import LanguageENUM
from ..models.normalized_statement_type_enum import NormalizedStatementTypeENUM
from ..types import UNSET, Unset
from typing import cast
import datetime






T = TypeVar("T", bound="DurableSkill")



@_attrs_define
class DurableSkill:
    """ Represents an individual element within a durable skills framework — either a skill statement or an organizational
    grouping that structures them.

    Durable skills frameworks organize their content hierarchically, and each framework uses its own vocabulary for the
    levels (for example "Competency" and "Component Skill" in XQ Competencies, or "Subskill" and "Indicator" in Carnegie
    Skills Progressions). Use `normalizedStatementType` for a classification that is consistent across frameworks, and
    `statementType` to see the framework's own label.

    These items are published outside the CASE Network, so they carry no CASE identifiers and are addressed by their
    Knowledge Graph `identifier`.

        Attributes:
            identifier (str): The unique identifier for this item in the Knowledge Graph system. This is a system-generated
                identifier that remains stable across data updates and can be used to reference this item in queries and
                relationships.
            author (str): The author or creator of this content, typically the organization that published the framework
            provider (str): The service provider or organization that makes this data available in the knowledge graph
            license_ (str): A URL to the license document that applies to this content
            attribution_statement (str): A textual credit that acknowledges the source and creator of this work, as required
                by the CC BY 4.0 license. If you display or redistribute this content, you must include this attribution
                statement to comply with the license terms.
            has_children (bool): True if this item has at least one direct child via the "hasChild" relationship. Use this
                flag to decide whether to render an expand/collapse affordance and whether a follow-up call to /durable-
                skills/{identifier}/children will return results, avoiding requests that yield empty pages.
            statement_code (None | str | Unset): A short, human-readable code that identifies this item within its
                framework, reflecting its position in the hierarchy (e.g. "COL.1.1A.1", "FK.AC.1.a"). This is the code
                practitioners use to reference the skill in materials and planning tools.
            name (None | str | Unset): A short label for this item. For progression levels this names the level reached
                (e.g. "Exploring", "Analyzing", "Integrating", "Extending"), which distinguishes sibling levels under the same
                parent. May be null for organizational groupings that carry no separate label.
            description (None | str | Unset): The full text of the skill statement or organizational element, describing
                what a learner should know or be able to do. May be null for purely structural groupings.
            statement_type (None | str | Unset): The classification label used by the source framework for this item (e.g.
                "Competency", "Component Skill", "Progression Level", "Subskill", "Indicator"). This preserves the framework's
                own terminology, which differs between frameworks. Use normalizedStatementType for cross-framework comparisons.
            normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that has been standardized
                across standards frameworks for cross-state queries and categorization
            grade_level (list[GradeLevelENUM] | None | Unset): The educational grade level(s) for which this item is
                intended
            jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
            in_language (LanguageENUM | Unset): Language used in the resource (BCP 47 format)
            date_created (datetime.date | None | Unset): The date on which this item was created in the source system
            date_modified (datetime.date | None | Unset): The date on which this item was most recently modified in the
                source system
            notes (None | str | Unset): Optional field containing additional context, commentary or usage guidance about
                this item
     """

    identifier: str
    author: str
    provider: str
    license_: str
    attribution_statement: str
    has_children: bool
    statement_code: None | str | Unset = UNSET
    name: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    statement_type: None | str | Unset = UNSET
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET
    grade_level: list[GradeLevelENUM] | None | Unset = UNSET
    jurisdiction: JurisdictionENUM | Unset = UNSET
    in_language: LanguageENUM | Unset = UNSET
    date_created: datetime.date | None | Unset = UNSET
    date_modified: datetime.date | None | Unset = UNSET
    notes: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

        has_children = self.has_children

        statement_code: None | str | Unset
        if isinstance(self.statement_code, Unset):
            statement_code = UNSET
        else:
            statement_code = self.statement_code

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        statement_type: None | str | Unset
        if isinstance(self.statement_type, Unset):
            statement_type = UNSET
        else:
            statement_type = self.statement_type

        normalized_statement_type: str | Unset = UNSET
        if not isinstance(self.normalized_statement_type, Unset):
            normalized_statement_type = self.normalized_statement_type.value


        grade_level: list[str] | None | Unset
        if isinstance(self.grade_level, Unset):
            grade_level = UNSET
        elif isinstance(self.grade_level, list):
            grade_level = []
            for grade_level_type_0_item_data in self.grade_level:
                grade_level_type_0_item = grade_level_type_0_item_data.value
                grade_level.append(grade_level_type_0_item)


        else:
            grade_level = self.grade_level

        jurisdiction: str | Unset = UNSET
        if not isinstance(self.jurisdiction, Unset):
            jurisdiction = self.jurisdiction.value


        in_language: str | Unset = UNSET
        if not isinstance(self.in_language, Unset):
            in_language = self.in_language.value


        date_created: None | str | Unset
        if isinstance(self.date_created, Unset):
            date_created = UNSET
        elif isinstance(self.date_created, datetime.date):
            date_created = self.date_created.isoformat()
        else:
            date_created = self.date_created

        date_modified: None | str | Unset
        if isinstance(self.date_modified, Unset):
            date_modified = UNSET
        elif isinstance(self.date_modified, datetime.date):
            date_modified = self.date_modified.isoformat()
        else:
            date_modified = self.date_modified

        notes: None | str | Unset
        if isinstance(self.notes, Unset):
            notes = UNSET
        else:
            notes = self.notes


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
            "hasChildren": has_children,
        })
        if statement_code is not UNSET:
            field_dict["statementCode"] = statement_code
        if name is not UNSET:
            field_dict["name"] = name
        if description is not UNSET:
            field_dict["description"] = description
        if statement_type is not UNSET:
            field_dict["statementType"] = statement_type
        if normalized_statement_type is not UNSET:
            field_dict["normalizedStatementType"] = normalized_statement_type
        if grade_level is not UNSET:
            field_dict["gradeLevel"] = grade_level
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if in_language is not UNSET:
            field_dict["inLanguage"] = in_language
        if date_created is not UNSET:
            field_dict["dateCreated"] = date_created
        if date_modified is not UNSET:
            field_dict["dateModified"] = date_modified
        if notes is not UNSET:
            field_dict["notes"] = notes

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

        has_children = d.pop("hasChildren")

        def _parse_statement_code(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        statement_code = _parse_statement_code(d.pop("statementCode", UNSET))


        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))


        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))


        def _parse_statement_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        statement_type = _parse_statement_type(d.pop("statementType", UNSET))


        _normalized_statement_type = d.pop("normalizedStatementType", UNSET)
        normalized_statement_type: NormalizedStatementTypeENUM | Unset
        if isinstance(_normalized_statement_type,  Unset):
            normalized_statement_type = UNSET
        else:
            normalized_statement_type = NormalizedStatementTypeENUM(_normalized_statement_type)




        def _parse_grade_level(data: object) -> list[GradeLevelENUM] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                grade_level_type_0 = []
                _grade_level_type_0 = data
                for grade_level_type_0_item_data in (_grade_level_type_0):
                    grade_level_type_0_item = GradeLevelENUM(grade_level_type_0_item_data)



                    grade_level_type_0.append(grade_level_type_0_item)

                return grade_level_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[GradeLevelENUM] | None | Unset, data)

        grade_level = _parse_grade_level(d.pop("gradeLevel", UNSET))


        _jurisdiction = d.pop("jurisdiction", UNSET)
        jurisdiction: JurisdictionENUM | Unset
        if isinstance(_jurisdiction,  Unset):
            jurisdiction = UNSET
        else:
            jurisdiction = JurisdictionENUM(_jurisdiction)




        _in_language = d.pop("inLanguage", UNSET)
        in_language: LanguageENUM | Unset
        if isinstance(_in_language,  Unset):
            in_language = UNSET
        else:
            in_language = LanguageENUM(_in_language)




        def _parse_date_created(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                date_created_type_0 = datetime.date.fromisoformat(data)



                return date_created_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        date_created = _parse_date_created(d.pop("dateCreated", UNSET))


        def _parse_date_modified(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                date_modified_type_0 = datetime.date.fromisoformat(data)



                return date_modified_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        date_modified = _parse_date_modified(d.pop("dateModified", UNSET))


        def _parse_notes(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        notes = _parse_notes(d.pop("notes", UNSET))


        durable_skill = cls(
            identifier=identifier,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            has_children=has_children,
            statement_code=statement_code,
            name=name,
            description=description,
            statement_type=statement_type,
            normalized_statement_type=normalized_statement_type,
            grade_level=grade_level,
            jurisdiction=jurisdiction,
            in_language=in_language,
            date_created=date_created,
            date_modified=date_modified,
            notes=notes,
        )


        durable_skill.additional_properties = d
        return durable_skill

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
