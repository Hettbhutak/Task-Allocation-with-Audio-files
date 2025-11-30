"""Property-based tests for dependency resolution."""

from hypothesis import given, strategies as st, settings

from src.models import ExtractedTask, TaskDependency
from src.dependency_resolver import DependencyResolver


# Strategy for dependency phrases
dependency_phrase_strategy = st.sampled_from([
    'depends on', 'after', 'once', 'blocked by', 'waiting for',
    'requires', 'needs', 'prerequisite'
])


# Feature: meeting-task-assignment, Property 12: Dependency phrase detection
# For any task description containing dependency phrases ("depends on", "after X is done",
# "blocked by"), the DependencyResolver SHALL identify and return a non-empty dependency
# relationship.
# **Validates: Requirements 8.1, 8.2**
@settings(max_examples=100)
@given(
    dep_phrase=st.sampled_from([
        'depends on the login fix',
        'after the database update is done',
        'once the api is completed',
        'blocked by the security review',
        'waiting for the design approval',
        'requires the setup to be completed first',
    ])
)
def test_dependency_phrase_detection(dep_phrase):
    """Property 12: Dependency phrases are detected in task text."""
    resolver = DependencyResolver()
    
    # Check that the phrase is detected
    assert resolver.has_dependency_phrase(dep_phrase), \
        f"Should detect dependency in: '{dep_phrase}'"


# Test that dependency phrases are extracted correctly
@settings(max_examples=50)
@given(
    prereq_task=st.sampled_from(['login fix', 'database update', 'api setup', 'security review']),
    dep_type=st.sampled_from(['depends on', 'blocked by', 'waiting for'])
)
def test_dependency_extraction(prereq_task, dep_type):
    """Dependency phrases are extracted from task text."""
    resolver = DependencyResolver()
    
    text = f"This task {dep_type} {prereq_task}."
    deps = resolver._extract_dependencies_from_text(text)
    
    assert len(deps) > 0, f"Should extract dependency from: '{text}'"
    assert any(prereq_task in d for d in deps), f"Should find '{prereq_task}' in dependencies"


# Feature: meeting-task-assignment, Property 13: Circular dependency detection
# For any set of dependencies forming a cycle (A→B→C→A), the DependencyResolver
# SHALL detect and flag the circular dependency.
# **Validates: Requirements 8.4**
@settings(max_examples=50)
@given(
    cycle_size=st.integers(min_value=2, max_value=5)
)
def test_circular_dependency_detection(cycle_size):
    """Property 13: Circular dependencies are detected."""
    resolver = DependencyResolver()
    
    # Create a cycle: 0 -> 1 -> 2 -> ... -> 0
    dependencies = []
    for i in range(cycle_size):
        next_idx = (i + 1) % cycle_size
        dependencies.append(TaskDependency(
            dependent_task_index=i,
            prerequisite_task_index=next_idx,
            dependency_phrase=f"task {i} depends on task {next_idx}"
        ))
    
    cycles = resolver.detect_circular_dependencies(dependencies)
    
    assert len(cycles) > 0, f"Should detect cycle in chain of {cycle_size} tasks"


# Test that non-circular dependencies don't trigger false positives
@settings(max_examples=50)
@given(
    chain_length=st.integers(min_value=2, max_value=5)
)
def test_linear_dependencies_no_cycle(chain_length):
    """Linear dependency chains should not be flagged as cycles."""
    resolver = DependencyResolver()
    
    # Create a linear chain: 0 <- 1 <- 2 <- ... (no cycle)
    dependencies = []
    for i in range(chain_length - 1):
        dependencies.append(TaskDependency(
            dependent_task_index=i + 1,
            prerequisite_task_index=i,
            dependency_phrase=f"task {i+1} depends on task {i}"
        ))
    
    cycles = resolver.detect_circular_dependencies(dependencies)
    
    assert len(cycles) == 0, f"Linear chain should not have cycles"


# Test dependency order (topological sort)
@settings(max_examples=50)
@given(
    num_tasks=st.integers(min_value=2, max_value=5)
)
def test_dependency_order_respects_prerequisites(num_tasks):
    """Dependency order should place prerequisites before dependents."""
    resolver = DependencyResolver()
    
    # Create simple chain: task 0 must come before task 1, etc.
    dependencies = []
    for i in range(num_tasks - 1):
        dependencies.append(TaskDependency(
            dependent_task_index=i + 1,
            prerequisite_task_index=i,
            dependency_phrase=f"task {i+1} depends on task {i}"
        ))
    
    order = resolver.get_dependency_order(num_tasks, dependencies)
    
    # Verify order respects dependencies
    for dep in dependencies:
        prereq_pos = order.index(dep.prerequisite_task_index)
        dep_pos = order.index(dep.dependent_task_index)
        assert prereq_pos < dep_pos, \
            f"Prerequisite {dep.prerequisite_task_index} should come before dependent {dep.dependent_task_index}"
