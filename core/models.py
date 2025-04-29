from dataclasses import dataclass, field
from typing import Optional, List, Any

@dataclass
class ListingData:
    """Holds structured data for a single car listing."""
    city: Optional[str] = None
    year: Optional[str] = None
    mileage: Optional[str] = None
    engine_type: Optional[str] = None
    engine_capacity: Optional[str] = None
    transmission: Optional[str] = None
    price: Optional[int | str] = None
    picture_count: int = 0
    picture_availability: bool = False
    listing_id: Optional[str] = None
    url: Optional[str] = None


@dataclass
class ListingPageData:
    """Holds structured data for detail car page."""
    price: Optional[int] = None
    seller_contact: Optional[int] = None

    area: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None

    year: Optional[int] = None
    mileage: Optional[int] = None
    engine_type: Optional[str] = None
    transmission: Optional[str] = None

    registered_in: Optional[str] = None
    colour: Optional[str] = None
    assembly: Optional[str] = None
    engine_capacity: Optional[int] = None
    body_type: Optional[str] = None
    last_updated: Optional[str] = None
    ad_reference: Optional[str] = None
    import_date: Optional[str] = None
    chassis_number: Optional[str] = None


@dataclass
class ComparisonSpec:
    """Holds data for a single row in the comparison table."""
    feature: Optional[str] = None
    values: List[Any] = field(default_factory=list) 

@dataclass
class ComparisonSection:
    """Holds data for a specific section (e.g., Engine, Transmission)."""
    title: Optional[str] = None
    specifications: List[ComparisonSpec] = field(default_factory=list)

@dataclass
class ComparisonResult:
    """Holds the overall comparison results."""
    car_names: List[Optional[str]] = field(default_factory=lambda: [None, None, None]) 
    prices: List[Optional[int]] = field(default_factory=lambda: [None, None, None]) 
    ratings: List[Optional[int]] = field(default_factory=lambda: [None, None, None]) 
    review_counts: List[Optional[int]] = field(default_factory=lambda: [None, None, None]) 
    sections: List[ComparisonSection] = field(default_factory=list)
    
    def __str__(self):
        result = "Comparison Result:\n"
        result += f"Car Names: {self.car_names}\n"
        result += f"Prices: {self.prices}\n"
        result += f"Ratings: {self.ratings}\n"
        result += f"Review Counts: {self.review_counts}\n"
        for section in self.sections:
            result += f"Section: {section.title}\n"
            for spec in section.specifications:
                result += f"  Feature: {spec.feature}, Values: {spec.values}\n"
        return result
    