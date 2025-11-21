# @description: 
# @author: licanglong
# @date: 2025/10/10 14:59
from dataclasses import dataclass, field, is_dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Union, Set, FrozenSet, Tuple, Generic, TypeVar

import pytest

from app.utils.typeutils import as_dataclass

T = TypeVar('T')


# =====================
#   定义复杂结构
# =====================

@dataclass
class Address:
    city: str
    zipcode: int
    location: Optional[Dict[str, float]] = None  # dict 嵌套基本类型


@dataclass
class Company:
    name: str
    founded: datetime
    capital: Decimal
    departments: List[str] = field(default_factory=list)
    branch_addresses: Dict[str, Address] = field(default_factory=dict)  # dict 嵌套 dataclass


@dataclass
class Employee:
    id: int
    name: str
    roles: Set[str]
    skills: FrozenSet[str]
    salary: Union[int, str]  # Union 类型测试
    info: Dict[str, Union[Decimal, str, int]]
    address: Address  # dataclass 嵌套 dataclass
    company: Optional[Company] = None  # Optional + dataclass
    tags: Tuple[str, ...] = ("default",)
    join_date: Optional[datetime] = None


# =====================
#   构造复杂测试数据
# =====================

@pytest.fixture
def complex_data():
    return {
        "ID": "123",  # 大小写混合，用于测试 ignore_case
        "Name": "Alice",
        "ROLES": ["Developer", "Reviewer"],
        "SKILLS": ["Python", "SQL", "Docker"],
        "salary": "10000",  # Union[str, int]
        "INFO": {
            "level": "Senior",
            "years": 5,
            "bonus": "1500.50"  # Decimal 测试
        },
        "ADDRESS": {
            "City": "Shanghai",
            "ZipCode": 200000,
            "Location": {"lat": 31.23, "lng": 121.47}
        },
        "Company": {
            "name": "TechCorp",
            "founded": "2020-05-10T10:30:00",
            "capital": "5000000.00",
            "Departments": ["R&D", "Sales", "HR"],
            "Branch_Addresses": {
                "HQ": {
                    "City": "Beijing",
                    "ZipCode": 100000,
                    "Location": {"lat": 39.90, "lng": 116.40}
                },
                "Sub": {
                    "City": "Shenzhen",
                    "ZipCode": 518000,
                    "Location": {"lat": 22.54, "lng": 114.06}
                }
            }
        },
        "Tags": ("engineer", "team-lead"),
        "Join_Date": "2021-04-01T09:00:00"
    }


@dataclass
class DpptResponseData(Generic[T]):
    code: Optional[str] = None
    data: Optional[T] = None
    message: Optional[str] = None


@dataclass
class UserInfo:
    id: int
    name: str
    create_time: Optional[datetime] = None


@dataclass
class DpptResponseError:
    Message: Optional[str] = None


@dataclass
class DpptResponseResult():
    RequestId: Optional[str] = None
    Data: Optional[DpptResponseData[UserInfo]] = None
    Error: Optional[DpptResponseError] = None


# =====================
#   测试函数
# =====================

def test_as_dataclass_complex(complex_data):
    """测试 as_dataclass 对多层嵌套、集合、Union、datetime、Decimal 的完整支持"""
    emp = as_dataclass(Employee, complex_data, ignore_case=True)

    # 基础验证
    assert is_dataclass(emp)
    assert emp.id == 123  # 字符串 → int 自动转换
    assert emp.name == "Alice"

    # Set / FrozenSet
    assert isinstance(emp.roles, set)
    assert "Developer" in emp.roles
    assert isinstance(emp.skills, frozenset)
    assert "Python" in emp.skills

    # Union / Optional
    assert isinstance(emp.salary, str) or isinstance(emp.salary, int)

    # Dict / Decimal
    assert emp.info["bonus"] == Decimal("1500.50")

    # dataclass 嵌套 dataclass
    assert emp.address.city == "Shanghai"
    assert emp.address.zipcode == 200000
    assert emp.address.location["lat"] == 31.23

    # datetime 自动解析
    assert isinstance(emp.join_date, datetime)
    assert emp.join_date.year == 2021

    # 嵌套公司
    assert emp.company.name == "TechCorp"
    assert isinstance(emp.company.capital, Decimal)
    assert emp.company.capital == Decimal("5000000.00")

    # 公司嵌套 dict[dataclass]
    hq = emp.company.branch_addresses["HQ"]
    assert isinstance(hq, Address)
    assert hq.city == "Beijing"
    assert hq.location["lng"] == 116.40

    # List / Tuple 测试
    assert emp.company.departments == ["R&D", "Sales", "HR"]
    assert emp.tags == ("engineer", "team-lead")

    # ignore_case 验证
    assert emp.address.city == "Shanghai"  # 来源于 "City"
    assert emp.company.branch_addresses["Sub"].city == "Shenzhen"


# =====================
#   额外测试：顶层 List/Dict 支持
# =====================

def test_as_dataclass_top_level_list():
    """测试顶层为 List[dataclass]"""
    data = [
        {"city": "A", "zipcode": 111},
        {"city": "B", "zipcode": 222}
    ]
    result = as_dataclass(List[Address], data)
    assert all(is_dataclass(x) for x in result)
    assert result[1].zipcode == 222
