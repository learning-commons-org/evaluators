from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.jurisdiction_enum import JurisdictionENUM
from ..models.language_enum import LanguageENUM
from ..types import UNSET, Unset
from typing import cast
import datetime






T = TypeVar("T", bound="DurableSkillsFramework")



@_attrs_define
class DurableSkillsFramework:
    """ Represents a complete durable skills framework published by an organization such as XQ Institute or the Carnegie
    Foundation for the Advancement of Teaching.

    Durable skills frameworks describe transferable competencies — collaboration, communication, critical thinking and
    similar — rather than subject-area academic content. They are published outside the CASE Network, so they carry no
    CASE identifiers and are addressed by their Knowledge Graph `identifier`.

        Attributes:
            identifier (str): The unique identifier for this framework in the Knowledge Graph system. This is a system-
                generated identifier that remains stable across data updates. Use it to retrieve the framework's skills via GET
                /durable-skills.
            author (str): The author or creator of this framework, typically the organization that published it
            provider (str): The service provider or organization that makes this data available in the knowledge graph
            license_ (str): A URL to the license document that applies to this content
            attribution_statement (str): A textual credit that acknowledges the source and creator of this work, as required
                by the CC BY 4.0 license. If you display or redistribute this framework, you must include this attribution
                statement to comply with the license terms.
            name (None | str | Unset): The name or title of the framework (e.g. "XQ Competencies", "Carnegie Skills
                Progressions")
            description (None | str | Unset): A description of the framework providing additional context about its
                structure, scope and origin
            jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
            in_language (LanguageENUM | Unset): Language used in the resource (BCP 47 format)
            is_current (bool | Unset): Whether this framework is currently in effect. Frameworks that have been superseded
                or retired are excluded from responses by default; set includeNonCurrent=true to retrieve them.
            date_created (datetime.date | None | Unset): The date on which this framework was created in the source system
            date_modified (datetime.date | None | Unset): The date on which this framework was most recently modified
     """

    identifier: str
    author: str
    provider: str
    license_: str
    attribution_statement: str
    name: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    jurisdiction: JurisdictionENUM | Unset = UNSET
    in_language: LanguageENUM | Unset = UNSET
    is_current: bool | Unset = UNSET
    date_created: datetime.date | None | Unset = UNSET
    date_modified: datetime.date | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

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

        jurisdiction: str | Unset = UNSET
        if not isinstance(self.jurisdiction, Unset):
            jurisdiction = self.jurisdiction.value


        in_language: str | Unset = UNSET
        if not isinstance(self.in_language, Unset):
            in_language = self.in_language.value


        is_current = self.is_current

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


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
        })
        if name is not UNSET:
            field_dict["name"] = name
        if description is not UNSET:
            field_dict["description"] = description
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if in_language is not UNSET:
            field_dict["inLanguage"] = in_language
        if is_current is not UNSET:
            field_dict["isCurrent"] = is_current
        if date_created is not UNSET:
            field_dict["dateCreated"] = date_created
        if date_modified is not UNSET:
            field_dict["dateModified"] = date_modified

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

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




        is_current = d.pop("isCurrent", UNSET)

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


        durable_skills_framework = cls(
            identifier=identifier,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            name=name,
            description=description,
            jurisdiction=jurisdiction,
            in_language=in_language,
            is_current=is_current,
            date_created=date_created,
            date_modified=date_modified,
        )


        durable_skills_framework.additional_properties = d
        return durable_skills_framework

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
