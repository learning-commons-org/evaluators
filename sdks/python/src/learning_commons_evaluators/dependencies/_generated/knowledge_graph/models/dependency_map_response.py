from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from typing import cast

if TYPE_CHECKING:
  from ..models.dependency import Dependency
  from ..models.pagination import Pagination





T = TypeVar("T", bound="DependencyMapResponse")



@_attrs_define
class DependencyMapResponse:
    """ 
        Attributes:
            dependencies (list[Dependency]): Dependency relationships between lesson groupings, grouped by source
            pagination (Pagination): Cursor-based pagination metadata
     """

    dependencies: list[Dependency]
    pagination: Pagination
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.dependency import Dependency # noqa: PLC0415
        from ..models.pagination import Pagination # noqa: PLC0415
        dependencies = []
        for dependencies_item_data in self.dependencies:
            dependencies_item = dependencies_item_data.to_dict()
            dependencies.append(dependencies_item)



        pagination = self.pagination.to_dict()


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "dependencies": dependencies,
            "pagination": pagination,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dependency import Dependency # noqa: PLC0415
        from ..models.pagination import Pagination # noqa: PLC0415
        d = dict(src_dict)
        dependencies = []
        _dependencies = d.pop("dependencies")
        for dependencies_item_data in (_dependencies):
            dependencies_item = Dependency.from_dict(dependencies_item_data)



            dependencies.append(dependencies_item)


        pagination = Pagination.from_dict(d.pop("pagination"))




        dependency_map_response = cls(
            dependencies=dependencies,
            pagination=pagination,
        )


        dependency_map_response.additional_properties = d
        return dependency_map_response

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
