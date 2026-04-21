package com.thesis.demo.repository;

import com.thesis.demo.model.Task;
import com.thesis.demo.model.TaskStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface TaskRepository extends JpaRepository<Task, Long> {
    List<Task> findByStatus(TaskStatus status);
}
