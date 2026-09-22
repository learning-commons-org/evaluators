from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="LearningComponentSummary")



@_attrs_define
class LearningComponentSummary:
    """ A lightweight representation of a LearningComponent containing only essential information.

    This summary format is used in relationship endpoints (standards to learning components) to keep responses fast and
    enable efficient traversal. To retrieve full details for a learning component, use the GET /learning-
    components/{identifier} endpoint.

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            attribution_statement (str): Statement that acknowledges the resource's author and provider, as required by the
                CC BY 4.0 license
            description (None | str | Unset): Description of the specific skill or concept represented
     """

    identifier: str
    author: str
    provider: str
    license_: str
    attribution_statement: str
    description: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
        })
        if description is not UNSET:
            field_dict["description"] = description

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))


        learning_component_summary = cls(
            identifier=identifier,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            description=description,
        )


        learning_component_summary.additional_properties = d
        return learning_component_summary

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
