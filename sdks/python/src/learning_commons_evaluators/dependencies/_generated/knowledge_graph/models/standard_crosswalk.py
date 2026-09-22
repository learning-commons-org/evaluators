from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.jurisdiction_enum import JurisdictionENUM
from ..types import UNSET, Unset
from typing import cast
from uuid import UUID






T = TypeVar("T", bound="StandardCrosswalk")



@_attrs_define
class StandardCrosswalk:
    """ Represents a crosswalk relationship between two standards, including similarity metrics based on shared learning
    components.

    Crosswalks connect mathematics standards bidirectionally based on measurable overlap of learning components:
    - **State → CCSS**: When querying with a state standard, this represents an aligned CCSS standard
    - **CCSS → State**: When querying with a CCSS standard, this represents an aligned state standard

    Each crosswalk includes quantitative measures that help understand the strength and nature of the alignment.

    The Jaccard similarity score measures the proportion of shared learning components between the two standards, with
    scores ranging from 0 (no overlap) to 1 (complete overlap). Higher scores indicate stronger similarity in content
    coverage.

        Attributes:
            case_identifier_uuid (UUID): CASE Network UUID for the resource
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            attribution_statement (str): Statement that acknowledges the resource's author and provider, as required by the
                CC BY 4.0 license
            statement_code (None | str | Unset): Code that identifies a standard within its standards framework (e.g.,
                "3.NF.A.1", "A.1B", "MP1"); `null` for organizational groupings without assigned codes
            description (None | str | Unset): Full text of the standard describing what students should know or be able to
                do
            jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
            jaccard (float | Unset): Jaccard score representing the proportion of shared components between a state and
                Common Core State Standards (CCSS) standard; calculated as `sharedLCCount / (stateLCCount + ccssLCCount -
                sharedLCCount)`
            state_lc_count (int | Unset): Number of components supporting the state standard
            ccss_lc_count (int | Unset): Number of components supporting the Common Core State Standards (CCSS) standard
            shared_lc_count (int | Unset): Number of components supporting both the state and Common Core State Standards
                (CCSS) standards
     """

    case_identifier_uuid: UUID
    author: str
    provider: str
    license_: str
    attribution_statement: str
    statement_code: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    jurisdiction: JurisdictionENUM | Unset = UNSET
    jaccard: float | Unset = UNSET
    state_lc_count: int | Unset = UNSET
    ccss_lc_count: int | Unset = UNSET
    shared_lc_count: int | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        case_identifier_uuid = str(self.case_identifier_uuid)

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

        statement_code: None | str | Unset
        if isinstance(self.statement_code, Unset):
            statement_code = UNSET
        else:
            statement_code = self.statement_code

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        jurisdiction: str | Unset = UNSET
        if not isinstance(self.jurisdiction, Unset):
            jurisdiction = self.jurisdiction.value


        jaccard = self.jaccard

        state_lc_count = self.state_lc_count

        ccss_lc_count = self.ccss_lc_count

        shared_lc_count = self.shared_lc_count


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "caseIdentifierUUID": case_identifier_uuid,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
        })
        if statement_code is not UNSET:
            field_dict["statementCode"] = statement_code
        if description is not UNSET:
            field_dict["description"] = description
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if jaccard is not UNSET:
            field_dict["jaccard"] = jaccard
        if state_lc_count is not UNSET:
            field_dict["stateLCCount"] = state_lc_count
        if ccss_lc_count is not UNSET:
            field_dict["ccssLCCount"] = ccss_lc_count
        if shared_lc_count is not UNSET:
            field_dict["sharedLCCount"] = shared_lc_count

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        case_identifier_uuid = UUID(d.pop("caseIdentifierUUID"))




        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

        def _parse_statement_code(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        statement_code = _parse_statement_code(d.pop("statementCode", UNSET))


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




        jaccard = d.pop("jaccard", UNSET)

        state_lc_count = d.pop("stateLCCount", UNSET)

        ccss_lc_count = d.pop("ccssLCCount", UNSET)

        shared_lc_count = d.pop("sharedLCCount", UNSET)

        standard_crosswalk = cls(
            case_identifier_uuid=case_identifier_uuid,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            statement_code=statement_code,
            description=description,
            jurisdiction=jurisdiction,
            jaccard=jaccard,
            state_lc_count=state_lc_count,
            ccss_lc_count=ccss_lc_count,
            shared_lc_count=shared_lc_count,
        )


        standard_crosswalk.additional_properties = d
        return standard_crosswalk

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
