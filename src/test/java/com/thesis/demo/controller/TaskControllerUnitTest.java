package com.thesis.demo.controller;

import com.thesis.demo.model.Task;
import com.thesis.demo.model.TaskStatus;
import com.thesis.demo.repository.TaskRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;
import java.util.Optional;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(TaskController.class)
class TaskControllerUnitTest {

    @Autowired
    MockMvc mockMvc;

    @MockitoBean
    TaskRepository repo;

    @Test
    void getAll_returnsEmptyList() throws Exception {
        when(repo.findAll()).thenReturn(List.of());
        mockMvc.perform(get("/api/tasks"))
                .andExpect(status().isOk())
                .andExpect(content().json("[]"));
    }

    @Test
    void getById_notFound_returns404() throws Exception {
        when(repo.findById(99L)).thenReturn(Optional.empty());
        mockMvc.perform(get("/api/tasks/99"))
                .andExpect(status().isNotFound());
    }

    @Test
    void create_validTask_returns201() throws Exception {
        Task saved = new Task("Fix pipeline", "Urgent");
        saved.setStatus(TaskStatus.TODO);

        when(repo.save(org.mockito.ArgumentMatchers.any())).thenReturn(saved);

        mockMvc.perform(post("/api/tasks")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {"title":"Fix pipeline","description":"Urgent"}
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.title").value("Fix pipeline"));
    }
}
